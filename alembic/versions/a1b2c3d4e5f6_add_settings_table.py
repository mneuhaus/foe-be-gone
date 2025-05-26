"""Add settings table for persistent key/value storage

Revision ID: a1b2c3d4e5f6
Revises: e3d5b1f9c2a7
Create Date: 2025-05-27 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'e3d5b1f9c2a7'
branch_labels = None
depends_on = None

def upgrade():
    # Create settings table if it does not already exist
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key VARCHAR PRIMARY KEY NOT NULL,
            value VARCHAR NOT NULL
        )
        """
    )

def downgrade():
    op.drop_table('settings')