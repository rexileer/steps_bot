"""Добавляет таблицу ledger_entries и enum-типы ownertype/operationtype"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg


revision = "4875c0abfa54"
down_revision = "13b296824c97"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ownertype') THEN
                CREATE TYPE ownertype AS ENUM ('user', 'family');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'operationtype') THEN
                CREATE TYPE operationtype AS ENUM (
                    'steps_accrual',
                    'purchase',
                    'promo_accrual',
                    'refund',
                    'manual_adjust',
                    'transfer'
                );
            END IF;
        END
        $$;
        """
    )

    ownertype = pg.ENUM("user", "family", name="ownertype", create_type=False)
    operationtype = pg.ENUM(
        "steps_accrual",
        "purchase",
        "promo_accrual",
        "refund",
        "manual_adjust",
        "transfer",
        name="operationtype",
        create_type=False,
    )

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_type", ownertype, nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("family_id", sa.Integer(), sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=True),
        sa.Column("operation", operationtype, nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "(owner_type = 'user' AND user_id IS NOT NULL AND family_id IS NULL) OR "
            "(owner_type = 'family' AND family_id IS NOT NULL AND user_id IS NULL)",
            name="ck_ledger_owner_fk",
        ),
    )

    op.create_index("ix_ledger_owner_created", "ledger_entries", ["owner_type", "created_at"])
    op.create_index("ix_ledger_user_created", "ledger_entries", ["user_id", "created_at"])
    op.create_index("ix_ledger_family_created", "ledger_entries", ["family_id", "created_at"])
    op.create_index("ix_ledger_operation_created", "ledger_entries", ["operation", "created_at"])

    # broadcasts are created in a later migration


def downgrade() -> None:
    op.drop_index("ix_ledger_operation_created", table_name="ledger_entries")
    op.drop_index("ix_ledger_family_created", table_name="ledger_entries")
    op.drop_index("ix_ledger_user_created", table_name="ledger_entries")
    op.drop_index("ix_ledger_owner_created", table_name="ledger_entries")
    op.drop_table("ledger_entries")
    # broadcasts cleanup is handled in its own migration
