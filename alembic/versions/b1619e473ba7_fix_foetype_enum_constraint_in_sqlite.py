"""Fix FoeType enum constraint in SQLite

Revision ID: b1619e473ba7
Revises: 805cb3a9eab6
Create Date: 2025-05-29 20:07:40.275400

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1619e473ba7'
down_revision: Union[str, None] = '805cb3a9eab6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite doesn't support ALTER COLUMN directly, so we need to recreate the table
    # with the correct enum constraint
    
    with op.batch_alter_table('foes', schema=None) as batch_op:
        # Drop the old enum constraint and recreate with uppercase values
        batch_op.alter_column('foe_type',
                              existing_type=sa.VARCHAR(),
                              type_=sa.String(),
                              existing_nullable=False)
    
    # Make sure all values are uppercase
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE foes SET foe_type = UPPER(foe_type);
    """))
    
    # Also ensure detections table is updated
    connection.execute(sa.text("""
        UPDATE detections SET detected_foe = UPPER(detected_foe) WHERE detected_foe IS NOT NULL;
    """))


def downgrade() -> None:
    """Downgrade schema."""
    # Revert to lowercase
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE foes SET foe_type = LOWER(foe_type);
    """))
    connection.execute(sa.text("""
        UPDATE detections SET detected_foe = LOWER(detected_foe) WHERE detected_foe IS NOT NULL;
    """))
