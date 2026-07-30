"""Telemetry and Contextual Request Tracing (Correlation ID Injection)."""

import uuid
from contextvars import ContextVar

import structlog

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Gets the current request correlation ID or generates a fresh one."""
    cid = correlation_id_var.get()
    if not cid:
        cid = str(uuid.uuid4())
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    """Explicitly sets the correlation ID for context tracing."""
    correlation_id_var.set(cid)
    structlog.contextvars.bind_contextvars(correlation_id=cid)
