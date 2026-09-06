"""Tests for NLP Specialist."""

from __future__ import annotations

import pytest

from app.specialists.nlp_specialist import NLPSpecialist, register


@pytest.fixture
def nlp() -> NLPSpecialist:
    return register()


class TestTokenize:
    @pytest.mark.asyncio
    async def test_basic_tokenization(self, nlp: NLPSpecialist):
        result = await nlp.tokenize("Hello world, this is a test.")
        assert result["count"] > 0
        assert "hello" in result["tokens"]
        assert "world" in result["tokens"]

    @pytest.mark.asyncio
    async def test_unique_count(self, nlp: NLPSpecialist):
        result = await nlp.tokenize("hello hello world")
        assert result["unique_count"] == 2


class TestSentiment:
    @pytest.mark.asyncio
    async def test_positive(self, nlp: NLPSpecialist):
        result = await nlp.sentiment("This is great and amazing!")
        assert result["label"] == "positive"
        assert result["score"] > 0

    @pytest.mark.asyncio
    async def test_negative(self, nlp: NLPSpecialist):
        result = await nlp.sentiment("This is terrible and awful.")
        assert result["label"] == "negative"
        assert result["score"] < 0

    @pytest.mark.asyncio
    async def test_neutral(self, nlp: NLPSpecialist):
        result = await nlp.sentiment("The book is on the table.")
        assert result["label"] == "neutral"


class TestKeywords:
    @pytest.mark.asyncio
    async def test_extracts_keywords(self, nlp: NLPSpecialist):
        result = await nlp.keywords("Python is great. Python is easy. Learn Python.", top_k=3)
        assert len(result["keywords"]) > 0
        words = [k["word"] for k in result["keywords"]]
        assert "python" in words

    @pytest.mark.asyncio
    async def test_top_k_respected(self, nlp: NLPSpecialist):
        result = await nlp.keywords("one two three four five six seven eight nine ten", top_k=5)
        assert len(result["keywords"]) <= 5


class TestEntities:
    @pytest.mark.asyncio
    async def test_emails(self, nlp: NLPSpecialist):
        result = await nlp.entities("Contact us at test@example.com for info.")
        assert "test@example.com" in result["emails"]

    @pytest.mark.asyncio
    async def test_urls(self, nlp: NLPSpecialist):
        result = await nlp.entities("Visit https://example.com for more.")
        assert "https://example.com" in result["urls"]

    @pytest.mark.asyncio
    async def test_capitalized(self, nlp: NLPSpecialist):
        result = await nlp.entities("John Smith works at Google.")
        assert any("John" in p or "Smith" in p or "Google" in p for p in result["capitalized_phrases"])


class TestSummarize:
    @pytest.mark.asyncio
    async def test_short_text_returns_as_is(self, nlp: NLPSpecialist):
        result = await nlp.summarize("Short text.")
        assert result["summary"] == "Short text."

    @pytest.mark.asyncio
    async def test_long_text_truncates(self, nlp: NLPSpecialist):
        text = "First sentence here. " * 5 + "Second sentence here. " * 5
        result = await nlp.summarize(text, max_sentences=2)
        assert result["summary_length"] <= len(text)


class TestAnalyzeColumn:
    @pytest.mark.asyncio
    async def test_basic_analysis(self, nlp: NLPSpecialist):
        values = ["Great product!", "Terrible experience.", "It was okay."]
        result = await nlp.analyze_column(values, "reviews")
        assert result["column"] == "reviews"
        assert result["row_count"] == 3
        assert "sentiment_distribution" in result
        assert "top_keywords" in result


class TestRegister:
    def test_register_returns_specialist(self):
        specialist = register()
        assert specialist.name == "nlp_specialist"
        assert specialist.description
