"""Tests for document parsing."""

from __future__ import annotations

import pytest

from app.rag.parser import parse_document, supported_extensions


class TestSupportedExtensions:
    def test_includes_common_types(self):
        exts = supported_extensions()
        assert ".txt" in exts
        assert ".md" in exts
        assert ".html" in exts
        assert ".pdf" in exts


class TestParseTxt:
    def test_parses_simple_text(self):
        content = b"Hello world, this is a test document."
        result = parse_document(content, "test.txt")
        assert result.text == "Hello world, this is a test document."
        assert result.metadata["type"] == "text"
        assert result.metadata["size_bytes"] == len(content)

    def test_handles_empty_content(self):
        result = parse_document(b"", "empty.txt")
        assert result.text == ""

    def test_handles_unicode(self):
        content = "Héllo wörld 🌍".encode("utf-8")
        result = parse_document(content, "unicode.txt")
        assert "Héllo" in result.text


class TestParseMarkdown:
    def test_parses_markdown(self):
        content = b"# Title\n\nSome **bold** text.\n\n- item 1\n- item 2"
        result = parse_document(content, "readme.md")
        assert "# Title" in result.text
        assert "item 1" in result.text
        assert result.metadata["type"] == "markdown"


class TestParseHtml:
    def test_extracts_visible_text(self):
        content = b"<html><body><h1>Title</h1><p>Hello world</p></body></html>"
        result = parse_document(content, "page.html")
        assert "Title" in result.text
        assert "Hello world" in result.text

    def test_removes_script_content(self):
        content = b"<html><body><script>alert('x')</script><p>Visible</p></body></html>"
        result = parse_document(content, "page.html")
        assert "Visible" in result.text
        assert "alert" not in result.text


class TestUnsupportedType:
    def test_raises_on_unknown_extension(self):
        with pytest.raises(ValueError, match="Unsupported file type"):
            parse_document(b"data", "file.xyz")
