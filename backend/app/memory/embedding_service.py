from __future__ import annotations

import hashlib
import random
from typing import Any

from app.config import get_settings

try:  # pragma: no cover - optional dependency
    from openai import AsyncOpenAI
except Exception:  # pragma: no cover - fallback
    AsyncOpenAI = None

settings = get_settings()
EMBEDDING_DIM = 1536


class EmbeddingService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key) if AsyncOpenAI and settings.openai_api_key else None

    async def embed_text(self, text: str) -> list[float]:
        if self.client is not None:
            try:
                response = await self.client.embeddings.create(
                    model="text-embedding-3-small", input=text
                )
                return [float(v) for v in response.data[0].embedding]
            except Exception:
                pass
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        return [round(rng.uniform(-1, 1), 6) for _ in range(EMBEDDING_DIM)]

