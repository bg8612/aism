"""add bot prompts table

Revision ID: 20260515_04
Revises: 20260514_03
Create Date: 2026-05-15 23:45:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260515_04"
down_revision = "20260514_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bot_prompts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt_key", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("bot_id", "prompt_key", name="uq_bot_prompts_bot_key"),
    )
    op.create_index("ix_bot_prompts_bot_id", "bot_prompts", ["bot_id"])


def downgrade() -> None:
    op.drop_index("ix_bot_prompts_bot_id", table_name="bot_prompts")
    op.drop_table("bot_prompts")
