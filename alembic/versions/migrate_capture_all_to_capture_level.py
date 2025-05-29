"""migrate capture_all_to_capture_level

Revision ID: migrate_capture_all_to_capture_level
Revises: b1619e473ba7
Create Date: 2025-05-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import select, update
from sqlalchemy.orm import Session


# revision identifiers, used by Alembic.
revision = 'migrate_capture_all_to_capture_level'
down_revision = 'b1619e473ba7'
branch_labels = None
depends_on = None


def upgrade():
    """Migrate capture_all_snapshots boolean to snapshot_capture_level integer."""
    # Get connection
    connection = op.get_bind()
    
    # Check if capture_all_snapshots exists and migrate to snapshot_capture_level
    result = connection.execute(
        sa.text("SELECT value FROM setting WHERE key = 'capture_all_snapshots'")
    ).first()
    
    if result:
        # Convert boolean to appropriate level
        # If capture_all_snapshots was true, set level to 3 (All Snapshots)
        # If false, set level to 1 (AI Detection - default)
        capture_all = result[0].lower() == 'true'
        capture_level = 3 if capture_all else 1
        
        # Insert or update snapshot_capture_level
        connection.execute(
            sa.text("""
                INSERT OR REPLACE INTO setting (key, value) 
                VALUES ('snapshot_capture_level', :level)
            """),
            {"level": str(capture_level)}
        )
        
        # Remove old capture_all_snapshots setting
        connection.execute(
            sa.text("DELETE FROM setting WHERE key = 'capture_all_snapshots'")
        )
    else:
        # No existing setting, create default
        connection.execute(
            sa.text("""
                INSERT OR REPLACE INTO setting (key, value) 
                VALUES ('snapshot_capture_level', '1')
            """)
        )


def downgrade():
    """Revert back to capture_all_snapshots boolean."""
    # Get connection
    connection = op.get_bind()
    
    # Check if snapshot_capture_level exists
    result = connection.execute(
        sa.text("SELECT value FROM setting WHERE key = 'snapshot_capture_level'")
    ).first()
    
    if result:
        # Convert level back to boolean
        # Level 3 = true (capture all), anything else = false
        capture_level = int(result[0])
        capture_all = 'true' if capture_level == 3 else 'false'
        
        # Insert or update capture_all_snapshots
        connection.execute(
            sa.text("""
                INSERT OR REPLACE INTO setting (key, value) 
                VALUES ('capture_all_snapshots', :capture_all)
            """),
            {"capture_all": capture_all}
        )
        
        # Remove snapshot_capture_level
        connection.execute(
            sa.text("DELETE FROM setting WHERE key = 'snapshot_capture_level'")
        )