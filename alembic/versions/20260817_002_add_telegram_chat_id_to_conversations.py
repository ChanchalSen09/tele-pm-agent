"""Add telegram_chat_id column to conversations table.

Revision ID: 002_add_telegram_chat_id_to_conversations
Revises: 001_initial_schema
Create Date: 2026-08-17 17:58:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_add_telegram_chat_id_to_conversations"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("conversations")]
    
    if "telegram_chat_id" not in columns:
        op.add_column("conversations", sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True))
        op.create_index("ix_conversations_telegram_chat_id", "conversations", ["telegram_chat_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("conversations")]
    
    if "telegram_chat_id" in columns:
        op.drop_index("ix_conversations_telegram_chat_id", table_name="conversations")
        op.drop_column("conversations", "telegram_chat_id")
