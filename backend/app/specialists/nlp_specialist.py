"""NLP/Text Specialist for text analysis tasks."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from app.core.registry import skill


_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "because", "but", "and", "or", "if", "while", "that", "this", "it",
    "its", "i", "me", "my", "we", "our", "you", "your", "he", "him",
    "his", "she", "her", "they", "them", "their", "what", "which", "who",
    "whom", "these", "those", "am",
}

_POSITIVE_WORDS = {
    "good", "great", "excellent", "amazing", "wonderful", "fantastic",
    "outstanding", "superb", "brilliant", "love", "happy", "pleased",
    "satisfied", "perfect", "best", "positive", "nice", "awesome",
    "delighted", "glad", "enjoy", "beautiful", "impressive", "remarkable",
    "exceptional", "favorable", "successful", "win", "winning", "recommend",
}

_NEGATIVE_WORDS = {
    "bad", "poor", "terrible", "awful", "horrible", "disappointing",
    "worst", "hate", "angry", "unhappy", "dissatisfied", "ugly",
    "failure", "failed", "failing", "broken", "useless", "waste",
    "regret", "complaint", "complain", "problem", "issues", "wrong",
    "slow", "difficult", "hard", "painful", "annoying", "frustrating",
}

_WORD_RE = re.compile(r"[a-zA-Z]+(?:'[a-z]+)?")


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _extract_keywords(text: str, top_k: int = 10) -> list[tuple[str, int]]:
    tokens = _tokenize(text)
    filtered = [t for t in tokens if t not in _STOPWORDS and len(t) > 2]
    return Counter(filtered).most_common(top_k)


def _sentiment_score(text: str) -> dict[str, Any]:
    tokens = set(_tokenize(text))
    pos = len(tokens & _POSITIVE_WORDS)
    neg = len(tokens & _NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return {"label": "neutral", "score": 0.0, "positive_words": pos, "negative_words": neg}
    raw_score = (pos - neg) / total
    if raw_score > 0.1:
        label = "positive"
    elif raw_score < -0.1:
        label = "negative"
    else:
        label = "neutral"
    return {"label": label, "score": round(raw_score, 3), "positive_words": pos, "negative_words": neg}


def _extract_entities(text: str) -> dict[str, list[str]]:
    entities: dict[str, list[str]] = {
        "emails": [],
        "urls": [],
        "dates": [],
        "capitalized_phrases": [],
    }
    entities["emails"] = re.findall(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", text)
    entities["urls"] = re.findall(r"https?://[^\s]+|www\.[^\s]+", text)
    entities["dates"] = re.findall(
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b",
        text,
        re.IGNORECASE,
    )
    cap_phrases = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
    entities["capitalized_phrases"] = list(set(cap_phrases))[:20]
    return entities


def _summarize(text: str, max_sentences: int = 3) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if len(sentences) <= max_sentences:
        return " ".join(sentences)
    keywords = dict(_extract_keywords(text, top_k=20))
    scored: list[tuple[float, int, str]] = []
    for i, sent in enumerate(sentences):
        tokens = _tokenize(sent)
        if not tokens:
            continue
        score = sum(keywords.get(t, 0) for t in tokens) / len(tokens)
        scored.append((score, i, sent))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = sorted(scored[:max_sentences], key=lambda x: x[1])
    return " ".join(s for _, _, s in top)


class NLPSpecialist:
    """NLP/Text Specialist for text analysis tasks.

    Provides skills for tokenization, sentiment analysis, keyword extraction,
    entity recognition, and text summarization.
    """

    name: str = "nlp_specialist"
    description: str = "Analyze text columns: tokenization, sentiment, entities, summarization"

    @skill("tokenize")
    async def tokenize(self, text: str) -> dict[str, Any]:
        tokens = _tokenize(text)
        return {"tokens": tokens, "count": len(tokens), "unique_count": len(set(tokens))}

    @skill("sentiment")
    async def sentiment(self, text: str) -> dict[str, Any]:
        return _sentiment_score(text)

    @skill("keywords")
    async def keywords(self, text: str, top_k: int = 10) -> dict[str, Any]:
        kws = _extract_keywords(text, top_k)
        return {
            "keywords": [{"word": w, "count": c} for w, c in kws],
            "total_unique_words": len(set(_tokenize(text))),
        }

    @skill("entities")
    async def entities(self, text: str) -> dict[str, Any]:
        return _extract_entities(text)

    @skill("summarize")
    async def summarize(self, text: str, max_sentences: int = 3) -> dict[str, Any]:
        summary = _summarize(text, max_sentences)
        return {
            "summary": summary,
            "original_length": len(text),
            "summary_length": len(summary),
            "compression_ratio": round(len(summary) / max(len(text), 1), 3),
        }

    @skill("analyze_column")
    async def analyze_column(self, values: list[str], column_name: str = "") -> dict[str, Any]:
        all_text = " ".join(str(v) for v in values if v)
        all_tokens = _tokenize(all_text)
        all_keywords = _extract_keywords(all_text, top_k=15)
        sentiments = {"positive": 0, "negative": 0, "neutral": 0}
        for val in values:
            if val:
                label = _sentiment_score(val)["label"]
                sentiments[label] += 1
        return {
            "column": column_name,
            "row_count": len(values),
            "total_tokens": len(all_tokens),
            "unique_tokens": len(set(all_tokens)),
            "avg_tokens_per_row": round(len(all_tokens) / max(len(values), 1), 1),
            "top_keywords": [{"word": w, "count": c} for w, c in all_keywords],
            "sentiment_distribution": sentiments,
        }


def register() -> NLPSpecialist:
    return NLPSpecialist()
