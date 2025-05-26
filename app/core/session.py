"""Enhanced database session management with proper error handling and context managers."""

import logging
from contextlib import contextmanager
from typing import Generator, TypeVar, Optional, Callable, Any

from sqlmodel import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import engine

logger = logging.getLogger(__name__)

T = TypeVar('T')


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Create a database session with proper error handling and automatic cleanup.
    
    This context manager ensures that:
    - Sessions are properly closed even if an error occurs
    - Database errors are logged with context
    - Transactions are rolled back on error
    
    Yields:
        Session: A SQLModel database session
        
    Example:
        with get_db_session() as session:
            user = session.get(User, user_id)
            session.add(user)
            session.commit()
    """
    session = Session(engine)
    try:
        yield session
    except SQLAlchemyError as e:
        logger.error(f"Database error occurred: {e}", exc_info=True)
        session.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in database session: {e}", exc_info=True)
        session.rollback()
        raise
    finally:
        session.close()


def with_db_session(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator that provides a database session to a function.
    
    The decorated function should accept 'session' as its first parameter.
    
    Args:
        func: Function to wrap with database session
        
    Returns:
        Wrapped function that manages database session
        
    Example:
        @with_db_session
        def get_user(session: Session, user_id: int) -> User:
            return session.get(User, user_id)
    """
    def wrapper(*args, **kwargs) -> T:
        with get_db_session() as session:
            return func(session, *args, **kwargs)
    
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


def transactional(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator that wraps a function in a database transaction.
    
    If the function completes successfully, the transaction is committed.
    If an exception occurs, the transaction is rolled back.
    
    Args:
        func: Function to wrap in a transaction
        
    Returns:
        Wrapped function with transaction management
        
    Example:
        @transactional
        def transfer_funds(session: Session, from_id: int, to_id: int, amount: float):
            # All operations here will be in a single transaction
            from_account = session.get(Account, from_id)
            to_account = session.get(Account, to_id)
            from_account.balance -= amount
            to_account.balance += amount
            session.add(from_account)
            session.add(to_account)
    """
    def wrapper(*args, **kwargs) -> T:
        # Check if session is provided
        session = kwargs.get('session') or (args[0] if args and isinstance(args[0], Session) else None)
        
        if not session:
            # No session provided, create one
            with get_db_session() as new_session:
                kwargs['session'] = new_session
                try:
                    result = func(*args, **kwargs)
                    new_session.commit()
                    return result
                except Exception:
                    new_session.rollback()
                    raise
        else:
            # Session provided, use it but don't commit (let caller handle it)
            return func(*args, **kwargs)
    
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


def safe_get(session: Session, model_class: type[T], id: Any) -> Optional[T]:
    """
    Safely get a model instance by ID with error handling.
    
    Args:
        session: Database session
        model_class: SQLModel class to query
        id: Primary key value
        
    Returns:
        Model instance or None if not found or error occurs
    """
    try:
        return session.get(model_class, id)
    except SQLAlchemyError as e:
        logger.error(f"Error fetching {model_class.__name__} with id {id}: {e}")
        return None


def safe_commit(session: Session) -> bool:
    """
    Safely commit a session with error handling.
    
    Args:
        session: Database session to commit
        
    Returns:
        True if commit succeeded, False otherwise
    """
    try:
        session.commit()
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error committing transaction: {e}")
        session.rollback()
        return False