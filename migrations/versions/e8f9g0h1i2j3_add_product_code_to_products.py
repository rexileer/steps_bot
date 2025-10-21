"""add product code to products

Revision ID: e8f9g0h1i2j3
Revises: d7e8f9g0h1i2
Create Date: 2025-10-21 12:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "e8f9g0h1i2j3"
down_revision = "d7e8f9g0h1i2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    try:
        op.add_column("products", sa.Column("product_code", sa.String(64), nullable=True))
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_column("products", "product_code")
    except Exception:
        pass
