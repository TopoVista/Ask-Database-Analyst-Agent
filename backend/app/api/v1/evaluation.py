"""API endpoints for evaluation benchmarks and security audit.

The /benchmarks/{id}/run endpoints execute built-in test cases inline —
no external dataset downloads, no heavy ML libraries.  All test data is
embedded directly so the endpoints work on the Render 512 MB free tier.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_current_user, get_db
from app.evaluation.security_audit import run_security_audit
from app.schemas.auth import AuthenticatedUser
from app.services.user_service import ensure_user

router = APIRouter(prefix="/evaluation", tags=["evaluation"])

# ── Inline test fixtures ─────────────────────────────────────────────────────

# NL→SQL test cases — schema-independent sanity checks using the
# sql_accuracy token-F1 metric already implemented in evaluation/metrics.py
_NLQ_CASES: list[dict[str, Any]] = [
    {
        "question": "Show total sales per region",
        "expected_sql": "SELECT region, SUM(sales) AS total_sales FROM orders GROUP BY region ORDER BY total_sales DESC",
    },
    {
        "question": "Count distinct customers",
        "expected_sql": "SELECT COUNT(DISTINCT customer_id) AS distinct_customers FROM customers",
    },
    {
        "question": "Top 5 products by revenue last month",
        "expected_sql": (
            "SELECT product_name, SUM(revenue) AS total_revenue "
            "FROM sales "
            "WHERE sale_date >= DATE('now', '-1 month') "
            "GROUP BY product_name "
            "ORDER BY total_revenue DESC "
            "LIMIT 5"
        ),
    },
    {
        "question": "Average order value by customer segment",
        "expected_sql": (
            "SELECT segment, AVG(order_value) AS avg_order_value "
            "FROM orders "
            "GROUP BY segment "
            "ORDER BY avg_order_value DESC"
        ),
    },
    {
        "question": "Monthly revenue trend for the current year",
        "expected_sql": (
            "SELECT strftime('%Y-%m', sale_date) AS month, SUM(revenue) AS monthly_revenue "
            "FROM sales "
            "WHERE strftime('%Y', sale_date) = strftime('%Y', 'now') "
            "GROUP BY month "
            "ORDER BY month"
        ),
    },
]

# EDA test cases — synthetic numeric series fed into TimeSeriesSpecialist
_EDA_CASES: list[dict[str, Any]] = [
    {
        "name": "increasing_trend",
        "values": [1.0, 2.1, 3.0, 4.2, 5.1, 6.0, 7.3, 8.1, 9.0, 10.2],
        "expected_trend_direction": "increasing",
    },
    {
        "name": "decreasing_trend",
        "values": [10.0, 9.1, 8.3, 7.5, 6.4, 5.2, 4.1, 3.0, 2.2, 1.1],
        "expected_trend_direction": "decreasing",
    },
    {
        "name": "flat_signal",
        "values": [5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
        "expected_trend_direction": "flat",
    },
    {
        "name": "anomaly_present",
        "values": [2.0, 2.1, 2.0, 1.9, 2.1, 20.0, 2.0, 1.8, 2.2, 2.0],
        "expected_change_points_count_gt": 0,
    },
]

# NLP sentiment test cases — fed into NLPSpecialist
_NLP_CASES: list[dict[str, Any]] = [
    {"text": "This product is amazing and I love it!", "expected_label": "positive"},
    {"text": "Terrible quality, completely broken and useless.", "expected_label": "negative"},
    {"text": "The package arrived on time.", "expected_label": "neutral"},
]


class BenchmarkRunRequest(BaseModel):
    connection_string: str | None = None  # only used for live NLQ execution (optional)


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/security-audit")
async def security_audit(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    """Run a security audit of the system.

    Checks SQL read-only enforcement, PII redaction, and auth configuration.
    """
    await ensure_user(db, current_user)
    audit = await run_security_audit()
    return audit.to_dict()


@router.get("/benchmarks")
async def list_benchmarks(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    """List available benchmark suites."""
    await ensure_user(db, current_user)

    return {
        "benchmarks": [
            {
                "id": "nlq_to_sql",
                "name": "NL→SQL Token Accuracy",
                "description": (
                    "Measures SQL generation accuracy against 5 ground-truth queries "
                    "using token-level F1 scoring."
                ),
                "metrics": ["sql_accuracy (token F1)", "avg_latency_ms"],
                "test_cases": len(_NLQ_CASES),
                "run_endpoint": "POST /api/v1/evaluation/benchmarks/nlq_to_sql/run",
            },
            {
                "id": "eda_correctness",
                "name": "EDA / Time-Series Correctness",
                "description": (
                    "Validates TimeSeriesSpecialist trend/change-point detection "
                    "on 4 synthetic numeric series."
                ),
                "metrics": ["trend_accuracy", "change_point_detection"],
                "test_cases": len(_EDA_CASES),
                "run_endpoint": "POST /api/v1/evaluation/benchmarks/eda_correctness/run",
            },
            {
                "id": "nlp_sentiment",
                "name": "NLP Sentiment Accuracy",
                "description": (
                    "Validates NLPSpecialist sentiment classification on 3 labeled texts."
                ),
                "metrics": ["sentiment_accuracy"],
                "test_cases": len(_NLP_CASES),
                "run_endpoint": "POST /api/v1/evaluation/benchmarks/nlp_sentiment/run",
            },
        ],
    }


@router.post("/benchmarks/nlq_to_sql/run")
async def run_nlq_benchmark(
    body: BenchmarkRunRequest = BenchmarkRunRequest(),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    """Run the NL→SQL token-F1 benchmark against 5 built-in test cases.

    Uses the SQL generator from the pipeline with a minimal schema stub.
    Falls back to token-overlap scoring only (no live DB execution needed).
    """
    await ensure_user(db, current_user)

    from app.evaluation.metrics import compute_sql_accuracy
    from app.services.llm_service import LLMService
    from app.agents.sql_generator_agent import SQLGeneratorAgent

    llm = LLMService()
    sql_gen = SQLGeneratorAgent(llm)

    stub_schema = (
        "Tables: orders(order_id, region, sales, order_value, customer_id, sale_date, segment), "
        "customers(customer_id, segment), "
        "sales(product_name, revenue, sale_date)"
    )

    cases: list[dict[str, Any]] = []
    total_f1 = 0.0
    passed = 0
    start = time.monotonic()

    for case in _NLQ_CASES:
        t0 = time.monotonic()
        case_result: dict[str, Any] = {"question": case["question"]}
        try:
            sql_result = await sql_gen.run(
                {"id": "bench", "description": case["question"]},
                stub_schema,
                [],
            )
            generated = sql_result.get("sql") or ""
            metric = compute_sql_accuracy(generated, case["expected_sql"])
            f1 = metric.value
            total_f1 += f1
            ok = f1 >= 0.5
            if ok:
                passed += 1
            case_result.update(
                {
                    "generated_sql": generated,
                    "expected_sql": case["expected_sql"],
                    "sql_accuracy": f1,
                    "passed": ok,
                    "latency_ms": round((time.monotonic() - t0) * 1000, 1),
                }
            )
        except Exception as exc:
            case_result.update({"error": str(exc), "passed": False, "sql_accuracy": 0.0})

        cases.append(case_result)

    total_ms = round((time.monotonic() - start) * 1000, 1)
    n = len(_NLQ_CASES)
    return {
        "benchmark_id": "nlq_to_sql",
        "total_cases": n,
        "passed": passed,
        "failed": n - passed,
        "accuracy": round(passed / max(n, 1), 4),
        "avg_sql_f1": round(total_f1 / max(n, 1), 4),
        "total_time_ms": total_ms,
        "cases": cases,
    }


@router.post("/benchmarks/eda_correctness/run")
async def run_eda_benchmark(
    body: BenchmarkRunRequest = BenchmarkRunRequest(),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    """Run EDA correctness benchmark using TimeSeriesSpecialist on synthetic data.

    No external dependencies — pure Python computation.
    """
    await ensure_user(db, current_user)

    from app.specialists.timeseries_specialist import TimeSeriesSpecialist

    spec = TimeSeriesSpecialist()
    cases: list[dict[str, Any]] = []
    passed = 0
    start = time.monotonic()

    for case in _EDA_CASES:
        case_result: dict[str, Any] = {"name": case["name"], "passed": False}
        try:
            analysis = await spec.full_analysis(case["values"], column_name=case["name"])
            checks: list[bool] = []

            if "expected_trend_direction" in case:
                actual = analysis.get("trend", {}).get("direction", "")
                ok = actual == case["expected_trend_direction"]
                checks.append(ok)
                case_result["trend_direction"] = actual
                case_result["expected_trend_direction"] = case["expected_trend_direction"]
                case_result["trend_correct"] = ok

            if "expected_change_points_count_gt" in case:
                actual_cp = len(analysis.get("change_points", []))
                ok = actual_cp > case["expected_change_points_count_gt"]
                checks.append(ok)
                case_result["change_points_detected"] = actual_cp
                case_result["change_points_correct"] = ok

            all_ok = all(checks) and len(checks) > 0
            case_result["passed"] = all_ok
            case_result["full_analysis"] = analysis
            if all_ok:
                passed += 1

        except Exception as exc:
            case_result["error"] = str(exc)

        cases.append(case_result)

    total_ms = round((time.monotonic() - start) * 1000, 1)
    n = len(_EDA_CASES)
    return {
        "benchmark_id": "eda_correctness",
        "total_cases": n,
        "passed": passed,
        "failed": n - passed,
        "accuracy": round(passed / max(n, 1), 4),
        "total_time_ms": total_ms,
        "cases": cases,
    }


@router.post("/benchmarks/nlp_sentiment/run")
async def run_nlp_benchmark(
    body: BenchmarkRunRequest = BenchmarkRunRequest(),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db=Depends(get_db),
):
    """Run NLP sentiment accuracy benchmark using NLPSpecialist.

    No external API calls — pure rule-based lexical classifier.
    """
    await ensure_user(db, current_user)

    from app.specialists.nlp_specialist import NLPSpecialist

    spec = NLPSpecialist()
    cases: list[dict[str, Any]] = []
    passed = 0
    start = time.monotonic()

    for case in _NLP_CASES:
        case_result: dict[str, Any] = {"text": case["text"][:80]}
        try:
            result = await spec.sentiment(case["text"])
            actual = result.get("label", "")
            ok = actual == case["expected_label"]
            if ok:
                passed += 1
            case_result.update(
                {
                    "expected": case["expected_label"],
                    "predicted": actual,
                    "score": result.get("score"),
                    "passed": ok,
                }
            )
        except Exception as exc:
            case_result.update({"error": str(exc), "passed": False})
        cases.append(case_result)

    total_ms = round((time.monotonic() - start) * 1000, 1)
    n = len(_NLP_CASES)
    return {
        "benchmark_id": "nlp_sentiment",
        "total_cases": n,
        "passed": passed,
        "failed": n - passed,
        "accuracy": round(passed / max(n, 1), 4),
        "total_time_ms": total_ms,
        "cases": cases,
    }
