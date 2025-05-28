"""Add performance indexes for detections and sound effectiveness

Revision ID: ae4702f5cd12
Revises: a77cec2745b6
Create Date: 2025-05-29 00:34:17.835287

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae4702f5cd12'
down_revision: Union[str, None] = 'a77cec2745b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add index on timestamp for detection queries
    op.create_index('idx_detections_timestamp', 'detections', ['timestamp'])
    
    # Add index on detected_foe for statistics queries
    op.create_index('idx_detections_detected_foe', 'detections', ['detected_foe'])
    
    # Add index on foe_type for sound effectiveness queries
    op.create_index('idx_sound_effectiveness_foe_type', 'sound_effectiveness', ['foe_type'])
    
    # Add index on sound_file for sound effectiveness queries
    op.create_index('idx_sound_effectiveness_sound_file', 'sound_effectiveness', ['sound_file'])
    
    # Add composite index on foe_type + sound_file for sound statistics
    op.create_index('idx_sound_effectiveness_foe_sound', 'sound_effectiveness', ['foe_type', 'sound_file'])
    
    # Add index on foe_type for sound statistics queries
    op.create_index('idx_sound_statistics_foe_type', 'sound_statistics', ['foe_type'])
    
    # Add index on sound_file for sound statistics queries  
    op.create_index('idx_sound_statistics_sound_file', 'sound_statistics', ['sound_file'])
    
    # Add composite index on foe_type + sound_file for sound statistics
    op.create_index('idx_sound_statistics_foe_sound', 'sound_statistics', ['foe_type', 'sound_file'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes in reverse order
    op.drop_index('idx_sound_statistics_foe_sound')
    op.drop_index('idx_sound_statistics_sound_file')
    op.drop_index('idx_sound_statistics_foe_type')
    op.drop_index('idx_sound_effectiveness_foe_sound')
    op.drop_index('idx_sound_effectiveness_sound_file')
    op.drop_index('idx_sound_effectiveness_foe_type')
    op.drop_index('idx_detections_detected_foe')
    op.drop_index('idx_detections_timestamp')
