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
    
    # Rename cdek_uuid to pvz_id
    op.alter_column("orders", "cdek_uuid", new_column_name="pvz_id", existing_type=sa.String(64))
    
    # Drop the old foreign key constraint on cdek_uuid (if it exists)
    # and add a new one for pvz_id pointing to pvz table
    op.drop_constraint("orders_cdek_uuid_fkey", "orders", type_="foreignkey")
    
    # Add new foreign key constraint
    op.create_foreign_key(
        "fk_orders_pvz_id",
        "orders",
        "pvz",
        ["pvz_id"],
        ["id"],
        ondelete="SET NULL"
    )


def downgrade() -> None:
    # Drop new foreign key
    op.drop_constraint("fk_orders_pvz_id", "orders", type_="foreignkey")
    
    # Rename pvz_id back to cdek_uuid
    op.alter_column("orders", "pvz_id", new_column_name="cdek_uuid", existing_type=sa.String(64))
    
    # Add track_code back
    op.add_column("orders", sa.Column("track_code", sa.String(32), nullable=True))
