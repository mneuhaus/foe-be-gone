"""Merge migration heads

Revision ID: 511fc8e10f6c
Revises: f8e9d7c6b5a4, migrate_capture_all_to_capture_level
Create Date: 2025-06-02 08:29:58.891252

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '511fc8e10f6c'
down_revision: Union[str, None] = ('f8e9d7c6b5a4', 'migrate_capture_all_to_capture_level')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
