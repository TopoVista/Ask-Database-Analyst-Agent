from __future__ import annotations

import hashlib
import math
import re
from typing import Any

from app.config import get_settings

try:  # pragma: no cover - optional dependency
    from openai import AsyncOpenAI
except Exception:  # pragma: no cover - fallback
    AsyncOpenAI = None

settings = get_settings()
EMBEDDING_DIM = 1536
_NGRAM = 3
_WORD_RE = re.compile(r"[a-z0-9_]+")


def _local_embed(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """Deterministic, dependency-free lexical embedding.

    Falls back to when no embedding API key is configured. It maps character
    n-grams of each word into a dense, normalized vector via stable hashing, so
    cosine similarity between two vectors is a *meaningful* measure of textual
    overlap — unlike a random vector, which would make ``VectorMemory``'s
    ``search_similar`` return garbage in local/offline mode.
    """
    if not text:
        return [0.0] * dim
    vec = [0.0] * dim
    lowered = text.lower()
    for token in _WORD_RE.findall(lowered):
        token = token.strip("_")
        if not token:
            continue
        ngrams = {token[i : i + _NGRAM] for i in range(max(1, len(token) - (_NGRAM - 1)))}
        if not ngrams:
            ngrams = {token}
        for gram in ngrams:
            idx = int(hashlib.md5(gram.encode("utf-8")).hexdigest(), 16) % dim
            vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [round(v / norm, 6) for v in vec]


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
        return _local_embed(text)

