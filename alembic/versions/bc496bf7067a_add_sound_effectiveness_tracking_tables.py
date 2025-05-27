"""Add sound effectiveness tracking tables

Revision ID: bc496bf7067a
Revises: 48837dbc7051
Create Date: 2025-05-27 00:37:35.054933

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'bc496bf7067a'
down_revision: Union[str, None] = '48837dbc7051'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create sound_effectiveness table
    op.create_table('sound_effectiveness',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('detection_id', sa.Integer(), nullable=False),
        sa.Column('foe_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('sound_file', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('playback_method', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('foes_before', sa.Integer(), nullable=False),
        sa.Column('foes_after', sa.Integer(), nullable=False),
        sa.Column('confidence_before', sa.Float(), nullable=False),
        sa.Column('confidence_after', sa.Float(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('wait_duration', sa.Integer(), nullable=False),
        sa.Column('result', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('effectiveness_score', sa.Float(), nullable=False),
        sa.Column('follow_up_image_path', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('notes', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(['detection_id'], ['detections.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create sound_statistics table
    op.create_table('sound_statistics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('foe_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('sound_file', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('total_uses', sa.Integer(), nullable=False),
        sa.Column('successful_uses', sa.Integer(), nullable=False),
        sa.Column('partial_uses', sa.Integer(), nullable=False),
        sa.Column('failed_uses', sa.Integer(), nullable=False),
        sa.Column('success_rate', sa.Float(), nullable=False),
        sa.Column('average_effectiveness', sa.Float(), nullable=False),
        sa.Column('first_used', sa.DateTime(), nullable=False),
        sa.Column('last_used', sa.DateTime(), nullable=False),
        sa.Column('last_updated', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for faster lookups
    op.create_index('idx_sound_stats_foe_sound', 'sound_statistics', ['foe_type', 'sound_file'], unique=True)
    
    # Create time_based_effectiveness table
    op.create_table('time_based_effectiveness',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('foe_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('hour_of_day', sa.Integer(), nullable=False),
        sa.Column('total_detections', sa.Integer(), nullable=False),
        sa.Column('successful_deterrents', sa.Integer(), nullable=False),
        sa.Column('average_effectiveness', sa.Float(), nullable=False),
        sa.Column('best_sound', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('best_sound_success_rate', sa.Float(), nullable=False),
        sa.Column('last_updated', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for time-based lookups
    op.create_index('idx_time_effectiveness_foe_hour', 'time_based_effectiveness', ['foe_type', 'hour_of_day'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('idx_time_effectiveness_foe_hour', table_name='time_based_effectiveness')
    op.drop_index('idx_sound_stats_foe_sound', table_name='sound_statistics')
    
    # Drop tables
    op.drop_table('time_based_effectiveness')
    op.drop_table('sound_statistics')
    op.drop_table('sound_effectiveness')