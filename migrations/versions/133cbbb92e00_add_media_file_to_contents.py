"""Добавляет колонку media_file в contents для пути к локальному файлу"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "add_media_file_to_contents"
down_revision = "4875c0abfa54"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет колонку media_file."""
    op.add_column(
        "contents",
        sa.Column("media_file", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    """Удаляет колонку media_file."""
    op.drop_column("contents", "media_file")
