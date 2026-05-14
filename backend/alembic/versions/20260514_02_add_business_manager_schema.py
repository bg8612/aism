"""add business manager schema

Revision ID: 20260514_02
Revises: 20260514_01
Create Date: 2026-05-14 23:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260514_02"
down_revision = "20260514_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bot_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("business_name", sa.Text(), nullable=False),
        sa.Column("business_description", sa.Text(), nullable=True),
        sa.Column("allowed_topics", sa.Text(), nullable=True),
        sa.Column("forbidden_topics", sa.Text(), nullable=True),
        sa.Column("offtopic_message", sa.Text(), nullable=False),
        sa.Column("fallback_message", sa.Text(), nullable=False),
        sa.Column("human_transfer_message", sa.Text(), nullable=False),
        sa.Column("answer_only_from_knowledge_base", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("collect_leads", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("bot_id", name="uq_bot_settings_bot_id"),
    )
    op.create_index("ix_bot_settings_bot_id", "bot_settings", ["bot_id"])

    op.create_table(
        "knowledge_blocks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_knowledge_blocks_bot_id", "knowledge_blocks", ["bot_id"])

    op.create_table(
        "bot_fields",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_key", sa.String(length=100), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("field_type", sa.String(length=50), nullable=False, server_default="text"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("validation_type", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("bot_id", "field_key", name="uq_bot_fields_bot_field_key"),
    )
    op.create_index("ix_bot_fields_bot_id", "bot_fields", ["bot_id"])

    op.create_table(
        "bot_questions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_id", sa.Integer(), sa.ForeignKey("bot_fields.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_bot_questions_bot_id", "bot_questions", ["bot_id"])
    op.create_index("ix_bot_questions_field_id", "bot_questions", ["field_id"])

    op.create_table(
        "human_questions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("end_user_id", sa.Integer(), sa.ForeignKey("end_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("reason", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="new"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_human_questions_bot_id", "human_questions", ["bot_id"])
    op.create_index("ix_human_questions_conversation_id", "human_questions", ["conversation_id"])
    op.create_index("ix_human_questions_lead_id", "human_questions", ["lead_id"])
    op.create_index("ix_human_questions_end_user_id", "human_questions", ["end_user_id"])


def downgrade() -> None:
    op.drop_index("ix_human_questions_end_user_id", table_name="human_questions")
    op.drop_index("ix_human_questions_lead_id", table_name="human_questions")
    op.drop_index("ix_human_questions_conversation_id", table_name="human_questions")
    op.drop_index("ix_human_questions_bot_id", table_name="human_questions")
    op.drop_table("human_questions")

    op.drop_index("ix_bot_questions_field_id", table_name="bot_questions")
    op.drop_index("ix_bot_questions_bot_id", table_name="bot_questions")
    op.drop_table("bot_questions")

    op.drop_index("ix_bot_fields_bot_id", table_name="bot_fields")
    op.drop_table("bot_fields")

    op.drop_index("ix_knowledge_blocks_bot_id", table_name="knowledge_blocks")
    op.drop_table("knowledge_blocks")

    op.drop_index("ix_bot_settings_bot_id", table_name="bot_settings")
    op.drop_table("bot_settings")
