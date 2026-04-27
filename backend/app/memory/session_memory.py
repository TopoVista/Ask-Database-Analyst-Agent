from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict
from typing import Any

from app.config import get_settings

try:  # pragma: no cover - optional dependency
    import redis.asyncio as redis_async
except Exception:  # pragma: no cover - fallback
    redis_async = None

settings = get_settings()
_SESSIONS: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_LOCK = asyncio.Lock()


class SessionMemory:
    def __init__(self, session_id: str) -> None:
        self.session_id = str(session_id)
        self._redis = None

    async def _get_redis(self):
        if self._redis is not None:
            return self._redis
        if redis_async is None or not settings.redis_url:
            self._redis = False
            return None
        try:
            self._redis = redis_async.from_url(settings.redis_url, decode_responses=True)
            await self._redis.ping()
        except Exception:
            self._redis = False
        return None if self._redis is False else self._redis

    async def get_history(self) -> list[str]:
        client = await self._get_redis()
        if client is not None:
            try:
                payload = await client.get(f"session:{self.session_id}")
                if not payload:
                    return []
                items = json.loads(payload)
                return [f"Q: {item['question']}\nA: {item['insight']}" for item in items]
            except Exception:
                pass

        async with _LOCK:
            item = _SESSIONS.get(self.session_id)
            if not item or time.time() > item[0]:
                return []
            return [f"Q: {entry['question']}\nA: {entry['insight']}" for entry in item[1]]

    async def add_entry(self, question: str, insight: str, ttl: int = 86400) -> None:
        client = await self._get_redis()
        if client is not None:
            try:
                key = f"session:{self.session_id}"
                payload = await client.get(key)
                items = json.loads(payload) if payload else []
                items.append({"question": question, "insight": insight})
                await client.set(key, json.dumps(items), ex=ttl)
                return
            except Exception:
                pass

        async with _LOCK:
            expires_at = time.time() + ttl
            _, items = _SESSIONS.get(self.session_id, (expires_at, []))
            items = list(items)
            items.append({"question": question, "insight": insight})
            _SESSIONS[self.session_id] = (expires_at, items)

