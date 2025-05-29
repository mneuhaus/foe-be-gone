"""Update foe_type values to uppercase and handle FISCHREIER

Revision ID: 805cb3a9eab6
Revises: ae4702f5cd12
Create Date: 2025-05-29 19:52:38.498931

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '805cb3a9eab6'
down_revision: Union[str, None] = 'ae4702f5cd12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # First, update any FISCHREIER values to UNKNOWN
    connection = op.get_bind()
    
    # Update foes table
    connection.execute(sa.text("""
        UPDATE foes SET foe_type = 'UNKNOWN' WHERE foe_type = 'FISCHREIER';
    """))
    
    # Update any lowercase values to uppercase in foes table
    connection.execute(sa.text("""
        UPDATE foes SET foe_type = 'RATS' WHERE LOWER(foe_type) = 'rats';
    """))
    
    connection.execute(sa.text("""
        UPDATE foes SET foe_type = 'CROWS' WHERE LOWER(foe_type) = 'crows';
    """))
    
    connection.execute(sa.text("""
        UPDATE foes SET foe_type = 'CATS' WHERE LOWER(foe_type) = 'cats';
    """))
    
    connection.execute(sa.text("""
        UPDATE foes SET foe_type = 'UNKNOWN' WHERE LOWER(foe_type) = 'unknown';
    """))
    
    # Also update detected_foe column in detections table
    connection.execute(sa.text("""
        UPDATE detections SET detected_foe = 'UNKNOWN' WHERE detected_foe = 'FISCHREIER';
    """))
    
    connection.execute(sa.text("""
        UPDATE detections SET detected_foe = 'RATS' WHERE LOWER(detected_foe) = 'rats';
    """))
    
    connection.execute(sa.text("""
        UPDATE detections SET detected_foe = 'CROWS' WHERE LOWER(detected_foe) = 'crows';
    """))
    
    connection.execute(sa.text("""
        UPDATE detections SET detected_foe = 'CATS' WHERE LOWER(detected_foe) = 'cats';
    """))
    
    connection.execute(sa.text("""
        UPDATE detections SET detected_foe = 'UNKNOWN' WHERE LOWER(detected_foe) = 'unknown';
    """))


def downgrade() -> None:
    """Downgrade schema."""
    # Revert to lowercase values
    connection = op.get_bind()
    
    # Update foes table
    connection.execute(sa.text("""
        UPDATE foes SET foe_type = 'rats' WHERE foe_type = 'RATS';
    """))
    
    connection.execute(sa.text("""
        UPDATE foes SET foe_type = 'crows' WHERE foe_type = 'CROWS';
    """))
    
    connection.execute(sa.text("""
        UPDATE foes SET foe_type = 'cats' WHERE foe_type = 'CATS';
    """))
    
    connection.execute(sa.text("""
        UPDATE foes SET foe_type = 'unknown' WHERE foe_type = 'UNKNOWN';
    """))
    
    # Update detections table
    connection.execute(sa.text("""
        UPDATE detections SET detected_foe = 'rats' WHERE detected_foe = 'RATS';
    """))
    
    connection.execute(sa.text("""
        UPDATE detections SET detected_foe = 'crows' WHERE detected_foe = 'CROWS';
    """))
    
    connection.execute(sa.text("""
        UPDATE detections SET detected_foe = 'cats' WHERE detected_foe = 'CATS';
    """))
    
    connection.execute(sa.text("""
        UPDATE detections SET detected_foe = 'unknown' WHERE detected_foe = 'UNKNOWN';
    """))
