"""Unit tests for TaskBoardCache."""

from app.core.cache import TaskBoardCache


def test_task_board_cache_operations() -> None:
    """Verifies get, set, and invalidation operations on TaskBoardCache."""
    cache = TaskBoardCache()
    chat_id = -1001

    assert cache.get(chat_id) is None

    cache.set(chat_id, "Sample Task Board Markdown")
    assert cache.get(chat_id) == "Sample Task Board Markdown"

    cache.invalidate(chat_id)
    assert cache.get(chat_id) is None
