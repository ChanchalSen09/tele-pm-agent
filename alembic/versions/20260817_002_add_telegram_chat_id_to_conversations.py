"""Add telegram_chat_id column to conversations and tasks tables.

Revision ID: 002_add_telegram_chat_id
Revises: 001_initial_schema
Create Date: 2026-08-17 18:05:00

"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_add_telegram_chat_id"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if context.is_offline_mode():
        op.add_column("conversations", sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True))
        op.create_index("ix_conversations_telegram_chat_id", "conversations", ["telegram_chat_id"])
        op.add_column("tasks", sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True))
        op.create_index("ix_tasks_telegram_chat_id", "tasks", ["telegram_chat_id"])
        return

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    conv_columns = [col["name"] for col in inspector.get_columns("conversations")]
    if "telegram_chat_id" not in conv_columns:
        op.add_column("conversations", sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True))
        op.create_index("ix_conversations_telegram_chat_id", "conversations", ["telegram_chat_id"])

    task_columns = [col["name"] for col in inspector.get_columns("tasks")]
    if "telegram_chat_id" not in task_columns:
        op.add_column("tasks", sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True))
        op.create_index("ix_tasks_telegram_chat_id", "tasks", ["telegram_chat_id"])


def downgrade() -> None:
    if context.is_offline_mode():
        op.drop_index("ix_tasks_telegram_chat_id", table_name="tasks")
        op.drop_column("tasks", "telegram_chat_id")
        op.drop_index("ix_conversations_telegram_chat_id", table_name="conversations")
        op.drop_column("conversations", "telegram_chat_id")
        return

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    task_columns = [col["name"] for col in inspector.get_columns("tasks")]
    if "telegram_chat_id" in task_columns:
        op.drop_index("ix_tasks_telegram_chat_id", table_name="tasks")
        op.drop_column("tasks", "telegram_chat_id")

    conv_columns = [col["name"] for col in inspector.get_columns("conversations")]
    if "telegram_chat_id" in conv_columns:
        op.drop_index("ix_conversations_telegram_chat_id", table_name="conversations")
        op.drop_column("conversations", "telegram_chat_id")
