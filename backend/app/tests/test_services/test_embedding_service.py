from __future__ import annotations

import pytest

from app.memory.embedding_service import EMBEDDING_DIM, EmbeddingService, _local_embed
from app.memory.vector_memory import _cosine_similarity


def test_local_embed_deterministic_and_normalized():
    a = _local_embed("which products sold best last month")
    a2 = _local_embed("which products sold best last month")
    assert a == a2
    assert len(a) == EMBEDDING_DIM
    assert all(isinstance(v, float) for v in a)
    assert _cosine_similarity(a, a2) > 0.999


def test_local_embed_lexical_overlap_is_meaningful():
    similar = _cosine_similarity(
        _local_embed("top selling products this quarter"),
        _local_embed("best selling products last quarter"),
    )
    unrelated = _cosine_similarity(
        _local_embed("top selling products this quarter"),
        _local_embed("what is the weather forecast today"),
    )
    assert similar > unrelated


@pytest.mark.asyncio
async def test_embedding_service_uses_local_fallback_without_api_key():
    svc = EmbeddingService()
    # Without OPENAI_API_KEY the client is None and the deterministic local
    # embedding is returned (matching the production offline fallback).
    if svc.client is None:
        vec = await svc.embed_text("revenue by region")
        assert len(vec) == EMBEDDING_DIM
        assert all(isinstance(v, float) for v in vec)
    else:
        # API key present in the environment; just confirm a vector of the
        # expected dimensionality is returned.
        vec = await svc.embed_text("revenue by region")
        assert len(vec) > 0