"""Merge test image migrations

Revision ID: 985e563bb6eb
Revises: 81eb41d20d3a, test_image_migration
Create Date: 2025-06-02 21:50:27.935785

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '985e563bb6eb'
down_revision: Union[str, None] = ('81eb41d20d3a', 'test_image_migration')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
