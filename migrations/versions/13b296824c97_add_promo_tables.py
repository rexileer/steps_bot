from alembic import op
import sqlalchemy as sa

revision = "13b296824c97"
down_revision = "3773100f0eb9"
branch_labels = None
depends_on = None


def upgrade():
    """
    Создаёт таблицы промогрупп и промокодов без сроков действия.
    """
    op.create_table(
        "promo_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=60), nullable=False, unique=True),
        sa.Column("discount_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("price_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(
            "discount_percent >= 0 AND discount_percent <= 100",
            name="ck_promo_groups_discount_percent",
        ),
        sa.CheckConstraint(
            "price_points >= 0",
            name="ck_promo_groups_price_points",
        ),
    )

    op.create_table(
        "promo_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("promo_groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("code", name="uq_promo_codes_code"),
        sa.CheckConstraint("max_uses >= 0", name="ck_promo_codes_max_uses"),
        sa.CheckConstraint("used_count >= 0", name="ck_promo_codes_used_count"),
    )
    op.create_index("ix_promo_codes_group_id", "promo_codes", ["group_id"])


def downgrade():
    """
    Удаляет таблицы промокодов.
    """
    op.drop_index("ix_promo_codes_group_id", table_name="promo_codes")
    op.drop_table("promo_codes")
    op.drop_table("promo_groups")
