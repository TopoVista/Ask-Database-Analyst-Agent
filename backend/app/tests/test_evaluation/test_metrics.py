"""Tests for evaluation metrics."""

from __future__ import annotations

import pytest

from app.evaluation.metrics import (
    MetricResult,
    compute_answer_accuracy,
    compute_sql_accuracy,
    compute_execution_accuracy,
)


class TestComputeSqlAccuracy:
    def test_identical_queries(self):
        sql = "SELECT * FROM users"
        result = compute_sql_accuracy(sql, sql)
        assert result.value == 1.0

    def test_completely_different(self):
        result = compute_sql_accuracy("SELECT a FROM t", "SELECT b FROM t")
        assert result.value < 1.0

    def test_both_empty(self):
        result = compute_sql_accuracy("", "")
        assert result.value == 1.0

    def test_one_empty(self):
        result = compute_sql_accuracy("SELECT * FROM t", "")
        assert result.value == 0.0

    def test_partial_overlap(self):
        result = compute_sql_accuracy(
            "SELECT name, age FROM users",
            "SELECT name FROM users",
        )
        assert 0.0 < result.value < 1.0

    def test_case_insensitive(self):
        result = compute_sql_accuracy("select * from users", "SELECT * FROM users")
        assert result.value == 1.0


class TestComputeAnswerAccuracy:
    def test_identical_results(self):
        data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        result = compute_answer_accuracy(data, data)
        assert result.value == 1.0

    def test_both_empty(self):
        result = compute_answer_accuracy([], [])
        assert result.value == 1.0

    def test_one_empty(self):
        result = compute_answer_accuracy([{"id": 1}], [])
        assert result.value == 0.0

    def test_partial_overlap(self):
        pred = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        truth = [{"id": 1, "name": "Alice"}, {"id": 3, "name": "Charlie"}]
        result = compute_answer_accuracy(pred, truth)
        assert 0.0 < result.value < 1.0

    def test_order_independent(self):
        pred = [{"id": 1}, {"id": 2}]
        truth = [{"id": 2}, {"id": 1}]
        result = compute_answer_accuracy(pred, truth)
        assert result.value == 1.0


class TestExecutionAccuracy:
    def test_delegates_to_answer_accuracy(self):
        pred = [{"x": 1}]
        truth = [{"x": 1}]
        result = compute_execution_accuracy(pred, truth)
        assert result.value == 1.0
