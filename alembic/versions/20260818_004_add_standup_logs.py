"""Add standup_logs table and checkin columns to tasks table.

Revision ID: 004_add_standup_logs
Revises: 003_add_due_date_to_tasks
Create Date: 2026-08-18 14:20:00

"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004_add_standup_logs"
down_revision: Union[str, None] = "003_add_due_date_to_tasks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if context.is_offline_mode():
        op.add_column("tasks", sa.Column("last_checkin_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column("tasks", sa.Column("progress_notes", sa.Text(), nullable=True))
        op.add_column("users", sa.Column("role", sa.String(length=50), server_default=sa.text("'MEMBER'"), nullable=False))

        op.create_table(
            "standup_logs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
            sa.Column("telegram_user_id", sa.BigInteger(), nullable=True),
            sa.Column("checkin_type", sa.String(length=50), server_default=sa.text("'DAILY_STANDUP'"), nullable=False),
            sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
            sa.Column("prompt_text", sa.Text(), nullable=False),
            sa.Column("user_response", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=50), server_default=sa.text("'PENDING'"), nullable=False),
        )
        op.create_index("ix_standup_logs_telegram_chat_id", "standup_logs", ["telegram_chat_id"])
        op.create_index("ix_standup_logs_telegram_user_id", "standup_logs", ["telegram_user_id"])
        op.create_index("ix_standup_logs_status", "standup_logs", ["status"])
        return

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    task_columns = [col["name"] for col in inspector.get_columns("tasks")]

    if "last_checkin_at" not in task_columns:
        op.add_column("tasks", sa.Column("last_checkin_at", sa.DateTime(timezone=True), nullable=True))

    if "progress_notes" not in task_columns:
        op.add_column("tasks", sa.Column("progress_notes", sa.Text(), nullable=True))

    user_columns = [col["name"] for col in inspector.get_columns("users")]
    if "role" not in user_columns:
        op.add_column("users", sa.Column("role", sa.String(length=50), server_default=sa.text("'MEMBER'"), nullable=False))

    tables = inspector.get_table_names()
    if "standup_logs" not in tables:
        op.create_table(
            "standup_logs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
            sa.Column("telegram_user_id", sa.BigInteger(), nullable=True),
            sa.Column("checkin_type", sa.String(length=50), server_default=sa.text("'DAILY_STANDUP'"), nullable=False),
            sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
            sa.Column("prompt_text", sa.Text(), nullable=False),
            sa.Column("user_response", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=50), server_default=sa.text("'PENDING'"), nullable=False),
        )
        op.create_index("ix_standup_logs_telegram_chat_id", "standup_logs", ["telegram_chat_id"])
        op.create_index("ix_standup_logs_telegram_user_id", "standup_logs", ["telegram_user_id"])
        op.create_index("ix_standup_logs_status", "standup_logs", ["status"])


def downgrade() -> None:
    if context.is_offline_mode():
        op.drop_table("standup_logs")
        op.drop_column("tasks", "progress_notes")
        op.drop_column("tasks", "last_checkin_at")
        return

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "standup_logs" in tables:
        op.drop_table("standup_logs")

    task_columns = [col["name"] for col in inspector.get_columns("tasks")]
    if "progress_notes" in task_columns:
        op.drop_column("tasks", "progress_notes")

    if "last_checkin_at" in task_columns:
        op.drop_column("tasks", "last_checkin_at")
