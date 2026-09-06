"""Document parser for multiple file types.

Supports plain text, Markdown, HTML, and PDF documents.
Each parser returns the extracted text content.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ParsedDocument:
    """Result of parsing a document."""

    text: str
    metadata: dict[str, Any]
    source: str


def _parse_txt(content: bytes, source: str) -> ParsedDocument:
    """Parse plain text files."""
    text = content.decode("utf-8", errors="replace")
    return ParsedDocument(
        text=text,
        metadata={"source": source, "type": "text", "size_bytes": len(content)},
        source=source,
    )


def _parse_markdown(content: bytes, source: str) -> ParsedDocument:
    """Parse Markdown files (treated as text with structure preserved)."""
    text = content.decode("utf-8", errors="replace")
    return ParsedDocument(
        text=text,
        metadata={"source": source, "type": "markdown", "size_bytes": len(content)},
        source=source,
    )


def _parse_html(content: bytes, source: str) -> ParsedDocument:
    """Parse HTML files, extracting visible text."""
    raw = content.decode("utf-8", errors="replace")
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw, "html.parser")
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()
        text = soup.get_text(separator="\n", strip=True)
    except ImportError:
        # Fallback: strip tags with regex if bs4 not available
        import re

        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\s+", " ", text).strip()

    return ParsedDocument(
        text=text,
        metadata={"source": source, "type": "html", "size_bytes": len(content)},
        source=source,
    )


def _parse_pdf(content: bytes, source: str) -> ParsedDocument:
    """Parse PDF files, extracting text from all pages."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        pages_text: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages_text.append(page_text.strip())
        text = "\n\n".join(pages_text)
        metadata = {
            "source": source,
            "type": "pdf",
            "size_bytes": len(content),
            "num_pages": len(reader.pages),
        }
    except ImportError:
        raise ImportError(
            "pypdf is required for PDF parsing. Install it with: pip install pypdf"
        )
    except Exception as e:
        raise ValueError(f"Failed to parse PDF '{source}': {e}")

    return ParsedDocument(text=text, metadata=metadata, source=source)


_PARSERS = {
    ".txt": _parse_txt,
    ".text": _parse_txt,
    ".md": _parse_markdown,
    ".markdown": _parse_markdown,
    ".html": _parse_html,
    ".htm": _parse_html,
    ".pdf": _parse_pdf,
}


def parse_document(content: bytes, source: str) -> ParsedDocument:
    """Parse a document from raw bytes.

    Args:
        content: Raw file bytes.
        source: Filename or identifier (used to determine file type).

    Returns:
        ParsedDocument with extracted text and metadata.

    Raises:
        ValueError: If the file type is unsupported.
    """
    ext = Path(source).suffix.lower()
    parser = _PARSERS.get(ext)
    if parser is None:
        supported = ", ".join(sorted(_PARSERS.keys()))
        raise ValueError(
            f"Unsupported file type '{ext}' for '{source}'. Supported: {supported}"
        )
    return parser(content, source)


def supported_extensions() -> frozenset[str]:
    """Return the set of supported file extensions."""
    return frozenset(_PARSERS.keys())
