"""Sentence-based document chunking.

Splits parsed documents into overlapping chunks suitable for embedding
and retrieval. Chunks are sized to balance context preservation with
embedding quality.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chunk:
    """A single chunk of a document."""

    text: str
    source: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: dict[str, Any] = field(default_factory=dict)


# Default chunk configuration
DEFAULT_CHUNK_SIZE = 512  # characters
DEFAULT_CHUNK_OVERLAP = 64  # characters

# Sentence boundary pattern (period, question mark, exclamation followed by space or end)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences, preserving the delimiter."""
    if not text:
        return []
    sentences = _SENTENCE_RE.split(text)
    return [s.strip() for s in sentences if s.strip()]


def chunk_text(
    text: str,
    source: str = "unknown",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    metadata: dict[str, Any] | None = None,
) -> list[Chunk]:
    """Split text into overlapping chunks.

    Uses sentence boundaries to avoid breaking mid-sentence where possible.
    Each chunk tracks its character offset in the original text.

    Args:
        text: The full text to chunk.
        source: Identifier for the source document.
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Characters of overlap between consecutive chunks.
        metadata: Additional metadata to attach to each chunk.

    Returns:
        List of Chunk objects.
    """
    if not text or not text.strip():
        return []

    base_metadata = metadata or {}
    sentences = _split_sentences(text)

    if not sentences:
        # If no sentence boundaries found, fall back to fixed-size chunks
        return _fixed_chunk(text, source, chunk_size, chunk_overlap, base_metadata)

    chunks: list[Chunk] = []
    current_text = ""
    current_start = 0
    chunk_index = 0
    overlap_buffer = ""

    for sentence in sentences:
        # Check if adding this sentence would exceed chunk size
        candidate = f"{current_text} {sentence}".strip() if current_text else sentence

        if len(candidate) <= chunk_size:
            current_text = candidate
        else:
            # Finalize current chunk if it has content
            if current_text:
                chunk = Chunk(
                    text=current_text,
                    source=source,
                    chunk_index=chunk_index,
                    start_char=current_start,
                    end_char=current_start + len(current_text),
                    metadata={**base_metadata, "chunk_method": "sentence"},
                )
                chunks.append(chunk)
                chunk_index += 1

                # Start new chunk with overlap from previous
                if chunk_overlap > 0 and len(current_text) > chunk_overlap:
                    overlap_buffer = current_text[-chunk_overlap:]
                    current_text = f"{overlap_buffer} {sentence}".strip()
                    # Adjust start char to account for overlap
                    current_start = current_start + len(current_text) - len(overlap_buffer) - len(sentence) - 1
                else:
                    current_text = sentence
                    # Find the position of this sentence in the original text
                    current_start = text.find(sentence, current_start)
            else:
                # Single sentence longer than chunk_size — split it
                current_text = sentence

    # Don't forget the last chunk
    if current_text:
        chunk = Chunk(
            text=current_text,
            source=source,
            chunk_index=chunk_index,
            start_char=current_start,
            end_char=current_start + len(current_text),
            metadata={**base_metadata, "chunk_method": "sentence"},
        )
        chunks.append(chunk)

    return chunks


def _fixed_chunk(
    text: str,
    source: str,
    chunk_size: int,
    chunk_overlap: int,
    base_metadata: dict[str, Any],
) -> list[Chunk]:
    """Fallback fixed-size chunking without sentence awareness."""
    chunks: list[Chunk] = []
    start = 0
    chunk_index = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text_slice = text[start:end]

        chunks.append(
            Chunk(
                text=chunk_text_slice,
                source=source,
                chunk_index=chunk_index,
                start_char=start,
                end_char=end,
                metadata={**base_metadata, "chunk_method": "fixed"},
            )
        )
        chunk_index += 1
        start += chunk_size - chunk_overlap

    return chunks
