"""Add due_date and priority columns to tasks table.

Revision ID: 003_add_due_date_to_tasks
Revises: 002_add_telegram_chat_id
Create Date: 2026-08-17 18:49:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import context, op

# revision identifiers, used by Alembic.
revision: str = "003_add_due_date_to_tasks"
down_revision: str | None = "002_add_telegram_chat_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        op.add_column("tasks", sa.Column("due_date", sa.DateTime(timezone=True), nullable=True))
        op.add_column("tasks", sa.Column("priority", sa.String(length=50), server_default=sa.text("'HIGH'"), nullable=False))
        return

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    task_columns = [col["name"] for col in inspector.get_columns("tasks")]

    if "due_date" not in task_columns:
        op.add_column("tasks", sa.Column("due_date", sa.DateTime(timezone=True), nullable=True))

    if "priority" not in task_columns:
        op.add_column("tasks", sa.Column("priority", sa.String(length=50), server_default=sa.text("'HIGH'"), nullable=False))


def downgrade() -> None:
    if context.is_offline_mode():
        op.drop_column("tasks", "priority")
        op.drop_column("tasks", "due_date")
        return

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    task_columns = [col["name"] for col in inspector.get_columns("tasks")]

    if "priority" in task_columns:
        op.drop_column("tasks", "priority")

    if "due_date" in task_columns:
        op.drop_column("tasks", "due_date")
