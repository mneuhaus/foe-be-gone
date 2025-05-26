"""Add ai_cost and played_sounds columns to detections

Revision ID: e3d5b1f9c2a7
Revises: 31accb542a5e
Create Date: 2025-05-26 23:45:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e3d5b1f9c2a7'
down_revision = '31accb542a5e'
branch_labels = None
depends_on = None

def upgrade():
    # Add ai_cost column
    op.add_column('detections', sa.Column('ai_cost', sa.Float(), nullable=True))
    # Add played_sounds JSON column
    op.add_column('detections', sa.Column('played_sounds', sa.JSON(), nullable=True))

def downgrade():
    # Drop played_sounds column
    op.drop_column('detections', 'played_sounds')
    # Drop ai_cost column
    op.drop_column('detections', 'ai_cost')