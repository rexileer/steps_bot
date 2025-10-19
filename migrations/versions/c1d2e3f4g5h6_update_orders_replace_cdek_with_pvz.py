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
    # Drop track_code column
    op.drop_column("orders", "track_code")
    
    # Clean up orphaned cdek_uuid values (set to NULL) to avoid FK constraint violation
    # Old cdek_uuid values from CDEK won't exist in the new pvz table, so they must be NULL
    op.execute(
        sa.text("UPDATE orders SET cdek_uuid = NULL WHERE cdek_uuid IS NOT NULL")
    )
    
    # Drop any index on cdek_uuid if it exists (PostgreSQL keeps it after rename)
    try:
        op.drop_index("ix_orders_cdek_uuid", table_name="orders")
    except Exception:
        pass  # Index might not exist
    
    # Rename cdek_uuid to pvz_id
    op.alter_column("orders", "cdek_uuid", new_column_name="pvz_id", existing_type=sa.String(64))
    
    # Add new foreign key constraint to pvz table
    # (The old FK on cdek_uuid will be automatically dropped when the column is renamed)
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
        pass  # FK might already exist


def downgrade() -> None:
    # Drop new foreign key
    try:
        op.drop_constraint("fk_orders_pvz_id", "orders", type_="foreignkey")
    except Exception:
        pass
    
    # Rename pvz_id back to cdek_uuid
    op.alter_column("orders", "pvz_id", new_column_name="cdek_uuid", existing_type=sa.String(64))
    
    # Add track_code back
    op.add_column("orders", sa.Column("track_code", sa.String(32), nullable=True))
    
    # Recreate index if needed
    try:
        op.create_index("ix_orders_cdek_uuid", "orders", ["cdek_uuid"])
    except Exception:
        pass

