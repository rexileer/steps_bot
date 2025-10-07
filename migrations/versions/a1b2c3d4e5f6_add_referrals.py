"""add referrals table

Revision ID: a1b2c3d4e5f6
Revises: 5f2d3e1addb4
Create Date: 2025-10-06 11:30:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "5f2d3e1addb4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "referrals",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("inviter_id", sa.BigInteger(), nullable=False),
        sa.Column("reward_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inviter_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_referral_user_id"),
    )
    op.create_index("ix_referrals_user_id", "referrals", ["user_id"])
    op.create_index("ix_referrals_inviter_id", "referrals", ["inviter_id"])


def downgrade() -> None:
    op.drop_index("ix_referrals_inviter_id", table_name="referrals")
    op.drop_index("ix_referrals_user_id", table_name="referrals")
    op.drop_table("referrals")


