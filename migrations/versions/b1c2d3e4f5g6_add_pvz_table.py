"""add pvz table

Revision ID: b1c2d3e4f5g6
Revises: a1b2c3d4e5f6
Create Date: 2025-10-18 10:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "b1c2d3e4f5g6"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pvz",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("full_address", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_pvz_full_address", "pvz", ["full_address"])


def downgrade() -> None:
    op.drop_index("ix_pvz_full_address", table_name="pvz")
    op.drop_table("pvz")
