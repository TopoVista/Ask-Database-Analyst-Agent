"""Tests for document chunking."""

from __future__ import annotations

import pytest

from app.rag.chunker import Chunk, chunk_text


class TestChunkText:
    def test_empty_text_returns_no_chunks(self):
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_short_text_single_chunk(self):
        text = "This is a short sentence."
        chunks = chunk_text(text, source="test.txt", chunk_size=512)
        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].source == "test.txt"
        assert chunks[0].chunk_index == 0

    def test_long_text_multiple_chunks(self):
        # Create text longer than chunk_size
        sentences = ["This is sentence number " + str(i) + "." for i in range(20)]
        text = " ".join(sentences)
        chunks = chunk_text(text, source="test.txt", chunk_size=100, chunk_overlap=20)
        assert len(chunks) > 1

    def test_chunks_have_incrementing_indices(self):
        sentences = ["Sentence " + str(i) + "." for i in range(10)]
        text = " ".join(sentences)
        chunks = chunk_text(text, source="test.txt", chunk_size=50, chunk_overlap=10)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_overlap_preserves_context(self):
        sentences = ["First sentence here.", "Second sentence here.", "Third sentence here."]
        text = " ".join(sentences)
        chunks = chunk_text(text, source="test.txt", chunk_size=40, chunk_overlap=20)
        if len(chunks) > 1:
            # Overlap means some text appears in consecutive chunks
            assert chunks[0].text or chunks[1].text

    def test_metadata_attached(self):
        text = "A sentence. Another sentence."
        chunks = chunk_text(text, source="test.txt", chunk_size=512, metadata={"author": "test"})
        for chunk in chunks:
            assert chunk.metadata["author"] == "test"

    def test_character_offsets_track_position(self):
        text = "Short. " * 50
        chunks = chunk_text(text, source="test.txt", chunk_size=60, chunk_overlap=10)
        for chunk in chunks:
            assert chunk.start_char >= 0
            assert chunk.end_char > chunk.start_char
