"""SQLAlchemy ORM Entities for Users, Conversations, Messages, AI Responses, and Audit Logs."""

import uuid
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base

# Postgres JSONB fallback to generic JSON for SQLite test compatibility
JSONType = JSONB().with_variant(JSON(), "sqlite")
UUIDType = UUID(as_uuid=True)


class UserModel(Base):
    """ORM Model representing user accounts (`users` table)."""

    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tier: Mapped[str] = mapped_column(String(50), default="standard", nullable=False)

    # Relationships
    conversations: Mapped[list["ConversationModel"]] = relationship(
        "ConversationModel", back_populates="user", cascade="all, delete-orphan"
    )


class ConversationModel(Base):
    """ORM Model representing conversation threads (`conversations` table)."""

    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    telegram_chat_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, index=True
    )
    title: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default="New Conversation"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    user: Mapped[UserModel] = relationship("UserModel", back_populates="conversations")
    messages: Mapped[list["MessageModel"]] = relationship(
        "MessageModel", back_populates="conversation", cascade="all, delete-orphan"
    )


class MessageModel(Base):
    """ORM Model representing individual conversation turns (`messages` table)."""

    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sender_role: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # 'user', 'assistant', 'system'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Relationships
    conversation: Mapped[ConversationModel] = relationship(
        "ConversationModel", back_populates="messages"
    )
    ai_response: Mapped["AIResponseModel | None"] = relationship(
        "AIResponseModel",
        back_populates="message",
        uselist=False,
        cascade="all, delete-orphan",
    )


class AIResponseModel(Base):
    """ORM Model representing LLM execution telemetry metrics (`ai_responses` table)."""

    __tablename__ = "ai_responses"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        ForeignKey("messages.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    prompt_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, nullable=True
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    finish_reason: Mapped[str] = mapped_column(
        String(50), default="STOP", nullable=False
    )

    # Relationships
    message: Mapped[MessageModel] = relationship(
        "MessageModel", back_populates="ai_response"
    )


class AuditLogModel(Base):
    """ORM Model representing security and system audit logs (`audit_logs` table)."""

    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    correlation_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, nullable=False, index=True
    )
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONType, nullable=False, default=dict
    )


class TaskModel(Base):
    """ORM Model representing project tasks (`tasks` table)."""

    __tablename__ = "tasks"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assignee_username: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default="TODO", nullable=False, index=True
    )  # 'TODO', 'IN_PROGRESS', 'BLOCKED', 'DONE'
    created_by_telegram_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    telegram_chat_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, index=True
    )


class OrganizationModel(Base):
    """ORM Model representing organization tenant accounts (`organizations` table)."""

    __tablename__ = "organizations"

    telegram_chat_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    org_name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_tier: Mapped[str] = mapped_column(
        String(50), default="standard", nullable=False
    )  # 'standard', 'pro', 'enterprise'
    monthly_token_limit: Mapped[int] = mapped_column(
        Integer, default=100000, nullable=False
    )
    tokens_consumed_this_month: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


