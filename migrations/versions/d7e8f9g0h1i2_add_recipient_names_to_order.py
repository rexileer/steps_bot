"""add recipient names to order

Revision ID: d7e8f9g0h1i2
Revises: c1d2e3f4g5h6
Create Date: 2025-10-19 18:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "d7e8f9g0h1i2"
down_revision = "c1d2e3f4g5h6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    try:
        op.add_column("orders", sa.Column("recipient_first_name", sa.String(100), nullable=True))
    except Exception:
        pass
    
    try:
        op.add_column("orders", sa.Column("recipient_last_name", sa.String(100), nullable=True))
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_column("orders", "recipient_last_name")
    except Exception:
        pass
    
    try:
        op.drop_column("orders", "recipient_first_name")
    except Exception:
        pass

