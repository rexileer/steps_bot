"""update orders: replace cdek_uuid with pvz_id, remove track_code

Revision ID: c1d2e3f4g5h6
Revises: b1c2d3e4f5g6
Create Date: 2025-10-18 10:01:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "c1d2e3f4g5h6"
down_revision = "b1c2d3e4f5g6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Try to drop track_code if it exists
    try:
        op.drop_column("orders", "track_code")
    except Exception:
        pass
    
    # Try to add pvz_id if it doesn't exist (might have been renamed or already exists)
    try:
        # Check if pvz_id already exists by trying to add it
        op.add_column("orders", sa.Column("pvz_id", sa.String(64), nullable=True))
    except Exception:
        # If it fails, try renaming cdek_uuid to pvz_id
        try:
            op.alter_column("orders", "cdek_uuid", new_column_name="pvz_id", existing_type=sa.String(64))
        except Exception:
            # Column pvz_id already exists or cdek_uuid doesn't exist, skip
            pass
    
    # Clean up orphaned pvz_id values
    try:
        op.execute(sa.text("UPDATE orders SET pvz_id = NULL WHERE pvz_id IS NOT NULL AND pvz_id NOT IN (SELECT id FROM pvz)"))
    except Exception:
        pass
    
    # Try to add foreign key if it doesn't exist
    try:
        op.create_foreign_key(
            "fk_orders_pvz_id",
            "orders",
            "pvz",
            ["pvz_id"],
            ["id"],
            ondelete="SET NULL"
        )
    except Exception:
        pass


def downgrade() -> None:
    # Try to drop foreign key
    try:
        op.drop_constraint("fk_orders_pvz_id", "orders", type_="foreignkey")
    except Exception:
        pass
    
    # Try to rename pvz_id back to cdek_uuid
    try:
        op.alter_column("orders", "pvz_id", new_column_name="cdek_uuid", existing_type=sa.String(64))
    except Exception:
        pass
    
    # Try to add track_code back
    try:
        op.add_column("orders", sa.Column("track_code", sa.String(32), nullable=True))
    except Exception:
        pass

