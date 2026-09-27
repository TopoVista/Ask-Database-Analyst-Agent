from __future__ import annotations

import asyncio
import hashlib
import time

from app.config import get_settings

settings = get_settings()
_LOCAL_CACHE: dict[str, tuple[float, str]] = {}
_LOCK = asyncio.Lock()


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class QueryCache:
    async def get(self, key: str) -> str | None:
        hashed = _hash_key(key)
        async with _LOCK:
            item = _LOCAL_CACHE.get(hashed)
            if not item:
                return None
            expires_at, value = item
            if time.time() > expires_at:
                _LOCAL_CACHE.pop(hashed, None)
                return None
            return value

    async def set(self, key: str, value: str, ttl: int = 300) -> None:
        hashed = _hash_key(key)
        async with _LOCK:
            now = time.time()
            for cache_key, (expires_at, _) in list(_LOCAL_CACHE.items()):
                if expires_at <= now:
                    _LOCAL_CACHE.pop(cache_key, None)
            max_entries = get_settings().max_local_cache_entries
            while len(_LOCAL_CACHE) >= max_entries:
                _LOCAL_CACHE.pop(next(iter(_LOCAL_CACHE)))
            _LOCAL_CACHE[hashed] = (time.time() + ttl, value)
