"""add clients and bot channels

Revision ID: 20260514_03
Revises: 20260514_02
Create Date: 2026-05-14 23:58:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260514_03"
down_revision = "20260514_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("contact_name", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=100), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.add_column("bots", sa.Column("client_id", sa.Integer(), nullable=True))
    op.create_index("ix_bots_client_id", "bots", ["client_id"])
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("bots") as batch_op:
            batch_op.create_foreign_key(
                "fk_bots_client_id_clients",
                "clients",
                ["client_id"],
                ["id"],
                ondelete="SET NULL",
            )
    else:
        op.create_foreign_key("fk_bots_client_id_clients", "bots", "clients", ["client_id"], ["id"], ondelete="SET NULL")

    op.create_table(
        "bot_channels",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel_type", sa.String(length=50), nullable=False),
        sa.Column("bot_token_encrypted", sa.Text(), nullable=False),
        sa.Column("bot_username", sa.String(length=255), nullable=True),
        sa.Column("webhook_secret", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("bot_id", "channel_type", name="uq_bot_channels_bot_channel_type"),
    )
    op.create_index("ix_bot_channels_bot_id", "bot_channels", ["bot_id"])


def downgrade() -> None:
    op.drop_index("ix_bot_channels_bot_id", table_name="bot_channels")
    op.drop_table("bot_channels")

    op.drop_constraint("fk_bots_client_id_clients", "bots", type_="foreignkey")
    op.drop_index("ix_bots_client_id", table_name="bots")
    op.drop_column("bots", "client_id")

    op.drop_table("clients")
