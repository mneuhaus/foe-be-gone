"""Add provider and provider_model tables for cloud AI integration

Revision ID: 63b1daa36d74
Revises: 511fc8e10f6c
Create Date: 2025-06-02 08:30:19.343642

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63b1daa36d74'
down_revision: Union[str, None] = '511fc8e10f6c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add provider tables
    op.create_table('provider',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('provider_type', sa.String(), nullable=False),
        sa.Column('api_key', sa.String(), nullable=True),
        sa.Column('api_base', sa.String(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_provider_name'), 'provider', ['name'], unique=True)
    
    op.create_table('providermodel',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('model_type', sa.String(), nullable=False),
        sa.Column('supports_vision', sa.Boolean(), nullable=False),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('cost_per_1k_tokens', sa.Float(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['provider_id'], ['provider.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop provider tables
    op.drop_table('providermodel')
    op.drop_index(op.f('ix_provider_name'), table_name='provider')
    op.drop_table('provider')
