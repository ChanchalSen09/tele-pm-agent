"""Task Board Caching Engine for High-Efficiency Response Serving."""

from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CachedBoardEntry:
    """Dataclass holding cached task board Markdown text."""

    board_text: str


class TaskBoardCache:
    """In-memory cache for rendered Task Board responses per chat_id."""

    def __init__(self) -> None:
        self._store: dict[int, CachedBoardEntry] = {}

    def get(self, chat_id: int | None) -> str | None:
        """Retrieves cached task board for target chat_id if available."""
        if chat_id is None or chat_id not in self._store:
            return None
        logger.debug("Task board cache hit", chat_id=chat_id)
        return self._store[chat_id].board_text

    def set(self, chat_id: int | None, board_text: str) -> None:
        """Caches rendered task board string for target chat_id."""
        if chat_id is None:
            return
        self._store[chat_id] = CachedBoardEntry(board_text=board_text)
        logger.debug("Task board cached", chat_id=chat_id)

    def invalidate(self, chat_id: int | None) -> None:
        """Invalidates task board cache entry upon task state changes."""
        if chat_id is not None and chat_id in self._store:
            del self._store[chat_id]
            logger.debug("Task board cache invalidated", chat_id=chat_id)

    def clear(self) -> None:
        """Clears entire task board cache store."""
        self._store.clear()


# Global singleton task board cache instance
default_task_board_cache = TaskBoardCache()
