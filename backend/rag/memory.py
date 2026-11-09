"""
Resilient memory adapter with Redis fallback for session management.

Provides a unified interface for conversation history that gracefully
degrades from Redis to in-memory when Redis is unavailable.
"""

from __future__ import annotations
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Optional
try:
    from langchain.memory import ConversationBufferWindowMemory
except (ImportError, ModuleNotFoundError):
    from langchain_classic.memory import ConversationBufferWindowMemory
from langchain_community.chat_message_histories import ChatMessageHistory, RedisChatMessageHistory

logger = logging.getLogger(__name__)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SESSION_TTL = int(os.getenv("SESSION_TTL", "86400"))  # 24 hours default


class MemoryBackend(ABC):
    """Abstract base for memory backends."""

    @abstractmethod
    def get_memory(self, session_id: str, window_size: int = 10) -> ConversationBufferWindowMemory:
        """Get a memory instance for the given session."""
        pass

    @abstractmethod
    def clear_session(self, session_id: str) -> bool:
        """Clear memory for a session."""
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if backend is available."""
        pass


class InMemoryBackend(MemoryBackend):
    """In-memory fallback - always available, no persistence."""

    def __init__(self):
        self._sessions: dict[str, ChatMessageHistory] = {}

    def get_memory(self, session_id: str, window_size: int = 10) -> ConversationBufferWindowMemory:
        if session_id not in self._sessions:
            self._sessions[session_id] = ChatMessageHistory()
        return ConversationBufferWindowMemory(
            chat_memory=self._sessions[session_id],
            k=window_size,
            return_messages=True,
        )

    def clear_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def is_healthy(self) -> bool:
        return True


class RedisBackend(MemoryBackend):
    """Redis-backed memory with TTL support."""

    def __init__(self, redis_url: str = REDIS_URL, ttl: int = SESSION_TTL):
        self.redis_url = redis_url
        self.ttl = ttl
        self._available = False
        self._check_connection()

    def _check_connection(self) -> None:
        """Test Redis connectivity on initialization."""
        try:
            # Test by creating a temporary history instance
            test_history = RedisChatMessageHistory(
                session_id="health_check",
                url=self.redis_url,
                ttl=1,
            )
            test_history.clear()
            self._available = True
            logger.info("[Memory] Redis backend available")
        except Exception as e:
            self._available = False
            logger.warning(f"[Memory] Redis unavailable, will use in-memory fallback: {e}")

    def get_memory(self, session_id: str, window_size: int = 10) -> ConversationBufferWindowMemory:
        if not self._available:
            raise RuntimeError("Redis backend not available")

        history = RedisChatMessageHistory(
            session_id=session_id,
            url=self.redis_url,
            ttl=self.ttl,
        )
        return ConversationBufferWindowMemory(
            chat_memory=history,
            k=window_size,
            return_messages=True,
        )

    def clear_session(self, session_id: str) -> bool:
        if not self._available:
            return False
        try:
            history = RedisChatMessageHistory(
                session_id=session_id,
                url=self.redis_url,
                ttl=self.ttl,
            )
            history.clear()
            return True
        except Exception as e:
            logger.error(f"[Memory] Failed to clear Redis session {session_id}: {e}")
            return False

    def is_healthy(self) -> bool:
        return self._available


class ResilientMemory:
    """
    Resilient memory manager that prefers Redis but falls back to in-memory.

    Usage:
        memory = ResilientMemory()
        mem = memory.get_memory("session_123")
        # Use mem as normal ConversationBufferWindowMemory
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        ttl: Optional[int] = None,
        window_size: int = 10,
    ):
        self.window_size = window_size
        self._redis_backend = RedisBackend(redis_url or REDIS_URL, ttl or SESSION_TTL)
        self._fallback_backend = InMemoryBackend()
        self._active_backend: MemoryBackend = (
            self._redis_backend if self._redis_backend.is_healthy()
            else self._fallback_backend
        )
        logger.info(f"[Memory] Active backend: {type(self._active_backend).__name__}")

    def get_memory(self, session_id: str, window_size: Optional[int] = None) -> ConversationBufferWindowMemory:
        """Get memory for session, with automatic fallback on Redis failure."""
        try:
            return self._active_backend.get_memory(session_id, window_size or self.window_size)
        except Exception as e:
            if self._active_backend is self._redis_backend:
                logger.warning(f"[Memory] Redis failed for {session_id}, falling back to in-memory: {e}")
                self._active_backend = self._fallback_backend
                return self._fallback_backend.get_memory(session_id, window_size or self.window_size)
            raise

    def clear_session(self, session_id: str) -> bool:
        """Clear session from active backend."""
        return self._active_backend.clear_session(session_id)

    def force_fallback(self) -> None:
        """Manually switch to in-memory backend."""
        if self._active_backend is not self._fallback_backend:
            logger.info("[Memory] Manually switching to in-memory fallback")
            self._active_backend = self._fallback_backend

    def try_restore_redis(self) -> bool:
        """Attempt to restore Redis backend if it was previously unavailable."""
        if self._active_backend is self._fallback_backend:
            self._redis_backend._check_connection()
            if self._redis_backend.is_healthy():
                self._active_backend = self._redis_backend
                logger.info("[Memory] Restored Redis backend")
                return True
        return False

    @property
    def backend_name(self) -> str:
        return type(self._active_backend).__name__

    @property
    def using_redis(self) -> bool:
        return self._active_backend is self._redis_backend


# Global instance for backward compatibility
_global_memory: Optional[ResilientMemory] = None


def get_resilient_memory(
    redis_url: Optional[str] = None,
    ttl: Optional[int] = None,
    window_size: int = 10,
) -> ResilientMemory:
    """Get or create the global resilient memory instance."""
    global _global_memory
    if _global_memory is None:
        _global_memory = ResilientMemory(redis_url, ttl, window_size)
    return _global_memory


def reset_global_memory() -> None:
    """Reset global memory (useful for testing)."""
    global _global_memory
    _global_memory = None