"""Add detection models

Revision ID: 666f84e4f8a3
Revises: 
Create Date: 2025-05-26 11:29:55.742091

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '666f84e4f8a3'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    # Create integration_instances table first
    op.create_table('integration_instances',
    sa.Column('id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('integration_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('config_json', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('status_message', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_integration_instances_integration_type'), 'integration_instances', ['integration_type'], unique=False)
    
    # Create devices table
    op.create_table('devices',
    sa.Column('id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('integration_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('device_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('model', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('device_metadata_json', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('capabilities_json', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('current_image_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('last_detection', sa.DateTime(), nullable=True),
    sa.Column('last_seen', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['integration_id'], ['integration_instances.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_devices_device_type'), 'devices', ['device_type'], unique=False)
    op.create_index(op.f('ix_devices_integration_id'), 'devices', ['integration_id'], unique=False)
    
    # Now create detections table
    op.create_table('detections',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('device_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('image_path', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('image_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('status', sa.Enum('PENDING', 'PROCESSED', 'DETERRED', 'FAILED', name='detectionstatus'), nullable=False),
    sa.Column('ai_response', sa.JSON(), nullable=True),
    sa.Column('processed_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('deterrent_actions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('detection_id', sa.Integer(), nullable=False),
    sa.Column('action_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('action_details', sa.JSON(), nullable=True),
    sa.Column('triggered_at', sa.DateTime(), nullable=False),
    sa.Column('success', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['detection_id'], ['detections.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('foes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('foe_type', sa.Enum('RODENT', 'CROW', 'CROW_LIKE', 'CAT', 'UNKNOWN', name='foetype'), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('bounding_box', sa.JSON(), nullable=True),
    sa.Column('detection_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['detection_id'], ['detections.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('foes')
    op.drop_table('deterrent_actions')
    op.drop_table('detections')
    op.drop_index(op.f('ix_devices_integration_id'), table_name='devices')
    op.drop_index(op.f('ix_devices_device_type'), table_name='devices')
    op.drop_table('devices')
    op.drop_index(op.f('ix_integration_instances_integration_type'), table_name='integration_instances')
    op.drop_table('integration_instances')
    # ### end Alembic commands ###
