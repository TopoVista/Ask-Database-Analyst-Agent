"""Evaluation metrics for NL→SQL and answer quality."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MetricResult:
    """A single metric result."""

    name: str
    value: float
    details: str = ""


def compute_sql_accuracy(predicted_sql: str, ground_truth_sql: str) -> MetricResult:
    """Compute SQL accuracy by normalized string comparison.

    Uses token-level overlap (F1) for partial credit.
    """
    pred_tokens = _normalize_sql(predicted_sql)
    truth_tokens = _normalize_sql(ground_truth_sql)

    if not pred_tokens and not truth_tokens:
        return MetricResult("sql_accuracy", 1.0, "Both queries empty")
    if not pred_tokens or not truth_tokens:
        return MetricResult("sql_accuracy", 0.0, "One query is empty")

    overlap = pred_tokens & truth_tokens
    precision = len(overlap) / len(pred_tokens) if pred_tokens else 0.0
    recall = len(overlap) / len(truth_tokens) if truth_tokens else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return MetricResult("sql_accuracy", round(f1, 4), f"P={precision:.2f} R={recall:.2f}")


def compute_answer_accuracy(predicted_answer: list[dict[str, Any]], ground_truth_answer: list[dict[str, Any]]) -> MetricResult:
    """Compute answer accuracy by comparing result sets.

    Uses row-level exact match with tolerance for ordering.
    """
    if not predicted_answer and not ground_truth_answer:
        return MetricResult("answer_accuracy", 1.0, "Both empty")
    if not predicted_answer or not ground_truth_answer:
        return MetricResult("answer_accuracy", 0.0, "One result set is empty")

    # Convert rows to comparable tuples
    def row_to_tuple(row: dict[str, Any]) -> tuple:
        return tuple(sorted((k, str(v)) for k, v in row.items()))

    pred_set = frozenset(row_to_tuple(r) for r in predicted_answer)
    truth_set = frozenset(row_to_tuple(r) for r in ground_truth_answer)

    overlap = pred_set & truth_set
    precision = len(overlap) / len(pred_set) if pred_set else 0.0
    recall = len(overlap) / len(truth_set) if truth_set else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return MetricResult("answer_accuracy", round(f1, 4), f"Rows: pred={len(pred_set)} truth={len(truth_set)} match={len(overlap)}")


def compute_execution_accuracy(predicted_results: list[dict[str, Any]], ground_truth_results: list[dict[str, Any]]) -> MetricResult:
    """Execution accuracy: do the results match when both queries execute?"""
    return compute_answer_accuracy(predicted_results, ground_truth_results)


def _normalize_sql(sql: str) -> set[str]:
    """Normalize SQL to a set of tokens for comparison."""
    import re

    # Lowercase, remove extra whitespace, split on non-alphanumeric
    normalized = sql.lower().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    tokens = re.findall(r"[a-z0-9_]+", normalized)
    return set(tokens)
