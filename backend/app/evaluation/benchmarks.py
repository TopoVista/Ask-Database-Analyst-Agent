"""Benchmark runner for NL→SQL and EDA evaluation."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from app.evaluation.metrics import MetricResult, compute_sql_accuracy, compute_answer_accuracy


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""

    name: str
    total_cases: int
    passed: int
    failed: int
    metrics: list[MetricResult] = field(default_factory=list)
    total_time_ms: float = 0.0
    cases: list[dict[str, Any]] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return self.passed / max(self.total_cases, 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "total_cases": self.total_cases,
            "passed": self.passed,
            "failed": self.failed,
            "accuracy": round(self.accuracy, 4),
            "total_time_ms": round(self.total_time_ms, 2),
            "metrics": [{"name": m.name, "value": m.value, "details": m.details} for m in self.metrics],
        }


@dataclass
class NLQTestCase:
    """A single NL→SQL test case."""

    question: str
    expected_sql: str
    expected_answer: list[dict[str, Any]] | None = None
    schema: str = ""
    connection_string: str = ""


@dataclass
class EDATestCase:
    """An EDA correctness test case."""

    dataset_path: str
    expected_stats: dict[str, Any] = field(default_factory=dict)
    expected_columns: list[str] = field(default_factory=list)


async def run_nlq_benchmark(
    test_cases: list[NLQTestCase],
    pipeline_factory: Callable,
) -> BenchmarkResult:
    """Run NL→SQL benchmark against test cases.

    Args:
        test_cases: List of NLQ test cases with expected SQL/answers.
        pipeline_factory: Callable that returns a pipeline with a `run` method.

    Returns:
        BenchmarkResult with accuracy metrics.
    """
    result = BenchmarkResult(name="nlq_to_sql", total_cases=len(test_cases), passed=0, failed=0)
    start = time.monotonic()

    for case in test_cases:
        case_result: dict[str, Any] = {"question": case.question, "passed": False}
        try:
            pipeline = pipeline_factory()
            generated_sql = await pipeline.generate_sql(
                question=case.question,
                schema=case.schema,
                connection_string=case.connection_string,
            )
            sql_metric = compute_sql_accuracy(generated_sql, case.expected_sql)
            case_result["sql_accuracy"] = sql_metric.value
            case_result["generated_sql"] = generated_sql
            case_result["expected_sql"] = case.expected_sql

            if case.expected_answer is not None:
                answer_metric = compute_answer_accuracy(
                    pipeline.last_results or [],
                    case.expected_answer,
                )
                case_result["answer_accuracy"] = answer_metric.value
                case_result["passed"] = sql_metric.value >= 0.8 and answer_metric.value >= 0.8
            else:
                case_result["passed"] = sql_metric.value >= 0.8

            if case_result["passed"]:
                result.passed += 1
            else:
                result.failed += 1
            result.metrics.append(sql_metric)
        except Exception as exc:
            case_result["error"] = str(exc)
            result.failed += 1
        result.cases.append(case_result)

    result.total_time_ms = (time.monotonic() - start) * 1000
    return result


async def run_eda_benchmark(
    test_cases: list[EDATestCase],
    profiler_factory: Callable,
) -> BenchmarkResult:
    """Run EDA benchmark against test cases.

    Args:
        test_cases: List of EDA test cases with expected statistics.
        profiler_factory: Callable that returns a profiler.

    Returns:
        BenchmarkResult with correctness metrics.
    """
    result = BenchmarkResult(name="eda_correctness", total_cases=len(test_cases), passed=0, failed=0)
    start = time.monotonic()

    for case in test_cases:
        case_result: dict[str, Any] = {"dataset": case.dataset_path, "passed": False}
        try:
            profiler = profiler_factory()
            profile = await profiler.profile(case.dataset_path)

            checks_passed = 0
            checks_total = 0

            # Check expected columns exist
            if case.expected_columns:
                checks_total += 1
                profile_columns = set(profile.get("columns", {}).keys())
                if all(col in profile_columns for col in case.expected_columns):
                    checks_passed += 1

            # Check expected stats
            for stat_key, stat_expected in case.expected_stats.items():
                checks_total += 1
                profile_stats = profile.get("statistics", {})
                if stat_key in profile_stats and profile_stats[stat_key] == stat_expected:
                    checks_passed += 1

            case_result["checks_passed"] = checks_passed
            case_result["checks_total"] = checks_total
            case_result["passed"] = checks_total > 0 and checks_passed == checks_total

            if case_result["passed"]:
                result.passed += 1
            else:
                result.failed += 1
        except Exception as exc:
            case_result["error"] = str(exc)
            result.failed += 1
        result.cases.append(case_result)

    result.total_time_ms = (time.monotonic() - start) * 1000
    return result
