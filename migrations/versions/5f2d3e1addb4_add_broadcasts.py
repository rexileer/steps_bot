"""add broadcasts table

Revision ID: 5f2d3e1addb4
Revises: 4875c0abfa54
Create Date: 2025-09-13 13:31:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg


revision = "5f2d3e1addb4"
down_revision = "133cbbb92e00"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure enum for broadcast status exists
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'broadcaststatus') THEN
                CREATE TYPE broadcaststatus AS ENUM ('pending', 'sent', 'failed');
            END IF;
        END
        $$;
        """
    )

    # Reuse existing mediatype enum (created earlier); do not recreate
    mediatype = pg.ENUM("none", "photo", "video", name="mediatype", create_type=False)
    bstatus = pg.ENUM("pending", "sent", "failed", name="broadcaststatus", create_type=False)

    op.create_table(
        "broadcasts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("media_type", mediatype, nullable=False, server_default="none"),
        sa.Column("telegram_file_id", sa.String(length=255), nullable=True),
        sa.Column("media_url", sa.String(length=1024), nullable=True),
        sa.Column("media_file", sa.String(length=1024), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", bstatus, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_broadcast_due", "broadcasts", ["status", "scheduled_at"])


def downgrade() -> None:
    op.drop_index("ix_broadcast_due", table_name="broadcasts")
    op.drop_table("broadcasts")
    try:
        pg.ENUM(name="broadcaststatus").drop(op.get_bind(), checkfirst=True)
    except Exception:
        pass


