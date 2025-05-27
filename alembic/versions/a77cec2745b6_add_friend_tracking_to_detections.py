"""add friend tracking to detections

Revision ID: a77cec2745b6
Revises: bc496bf7067a
Create Date: 2025-05-27 07:40:46.495435

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a77cec2745b6'
down_revision: Union[str, None] = 'bc496bf7067a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('detections', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_friend', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('friend_type', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('friend_confidence', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('detected_foe', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('deterrent_effective', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('ai_analysis', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('detections', schema=None) as batch_op:
        batch_op.drop_column('created_at')
        batch_op.drop_column('ai_analysis')
        batch_op.drop_column('deterrent_effective')
        batch_op.drop_column('detected_foe')
        batch_op.drop_column('friend_confidence')
        batch_op.drop_column('friend_type')
        batch_op.drop_column('is_friend')
