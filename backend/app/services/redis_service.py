import logging
import time
from typing import Optional, Any, Dict, List

from app.core.config import settings

logger = logging.getLogger(__name__)

_MemoryValue = Any  # (value, expires_at or None) stored as a tuple


class RedisClient:
    """Thin wrapper around Redis for rate limiting, caching, locks and temporary state.

    Gracefully degrades to in-memory operations when Redis is unavailable, so the
    app remains demoable without infra. The in-memory fallback honors TTLs so
    rate-limit windows reset correctly even without Redis.
    """

    def __init__(self):
        self.redis = None
        self._memory: Dict[str, _MemoryValue] = {}
        try:
            import redis

            self.redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
            self.redis.ping()
            logger.info("Redis connected at %s", settings.REDIS_URL)
        except Exception as e:
            self.redis = None
            logger.warning(
                "Redis unavailable (%s). Falling back to in-memory store. "
                "Set REDIS_URL to a valid Redis instance to enable distributed state.",
                e,
            )

    @property
    def enabled(self) -> bool:
        return self.redis is not None

    # ---------------- in-memory helpers ----------------

    def _mem_get(self, key: str) -> Optional[str]:
        entry = self._memory.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at is not None and expires_at < time.monotonic():
            self._memory.pop(key, None)
            return None
        return value

    def _mem_set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        expires_at = time.monotonic() + ex if ex else None
        self._memory[key] = (value, expires_at)

    def _mem_incr(self, key: str, amount: int, ex: Optional[int] = None) -> int:
        base = int(self._mem_get(key) or 0)
        value = base + amount
        self._mem_set(key, str(value), ex)
        return value

    # ---------------- public API ----------------

    def get(self, key: str) -> Optional[str]:
        if self.redis:
            return self.redis.get(key)
        return self._mem_get(key)

    def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        if self.redis:
            self.redis.set(key, value, ex=ex)
        else:
            self._mem_set(key, value, ex)

    def delete(self, key: str) -> None:
        if self.redis:
            self.redis.delete(key)
        else:
            self._memory.pop(key, None)

    def incr(self, key: str, ex: Optional[int] = None) -> int:
        if self.redis:
            val = self.redis.incr(key)
            if ex:
                self.redis.expire(key, ex)
            return val
        return self._mem_incr(key, 1, ex)

    def incrby(self, key: str, amount: int, ex: Optional[int] = None) -> int:
        if self.redis:
            val = self.redis.incrby(key, amount)
            if ex:
                self.redis.expire(key, ex)
            return val
        return self._mem_incr(key, amount, ex)

    def expire(self, key: str, seconds: int) -> None:
        if self.redis:
            self.redis.expire(key, seconds)
        else:
            entry = self._memory.get(key)
            if entry is not None:
                self._memory[key] = (entry[0], time.monotonic() + seconds)

    def ttl(self, key: str) -> int:
        if self.redis:
            return self.redis.ttl(key)
        entry = self._memory.get(key)
        if entry is None:
            return -1
        value, expires_at = entry
        if expires_at is None:
            return -1
        now = time.monotonic()
        if now >= expires_at:
            # expired — purge lazily
            self._memory.pop(key, None)
            return -2
        return max(int(expires_at - now) + 1, 1)

    def lpush(self, key: str, value: str) -> None:
        if self.redis:
            self.redis.lpush(key, value)
        else:
            current = self._memory.get(key)
            items: list = list(current[0]) if current else []
            items.insert(0, value)
            expires_at = current[1] if current else None
            self._memory[key] = (items, expires_at)

    def lrange(self, key: str, start: int = 0, end: int = -1) -> List[str]:
        if self.redis:
            return self.redis.lrange(key, start, end)
        current = self._memory.get(key)
        items: list = list(current[0]) if current else []
        if end < 0:
            return items[start:]
        return items[start : end + 1]

    def rate_limit_check(self, key: str, limit: int, window_seconds: int) -> bool:
        """Return True if within limit, False if limited."""
        current = self.incr(key, ex=window_seconds)
        return current <= limit

    def acquire_lock(self, key: str, token: str, ttl_seconds: int = 30) -> bool:
        """Try to acquire a distributed lock. Returns True if acquired."""
        if self.redis:
            return bool(self.redis.set(key, token, nx=True, ex=ttl_seconds))
        if self._mem_get(key) is None:
            self._mem_set(key, token, ttl_seconds)
            return True
        return False

    def release_lock(self, key: str, token: str) -> bool:
        if self.redis:
            if self.redis.get(key) == token:
                self.redis.delete(key)
                return True
            return False
        if self._mem_get(key) == token:
            self._memory.pop(key, None)
            return True
        return False


redis_client = RedisClient()