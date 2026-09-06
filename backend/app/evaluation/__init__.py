"""Evaluation harness for benchmarking system performance.

Provides NL→SQL accuracy measurement, EDA correctness checks,
and dashboard narrative quality rubrics.
"""

from app.evaluation.benchmarks import BenchmarkResult, run_nlq_benchmark, run_eda_benchmark
from app.evaluation.security_audit import SecurityAudit, run_security_audit
from app.evaluation.metrics import compute_sql_accuracy, compute_answer_accuracy

__all__ = [
    "BenchmarkResult",
    "run_nlq_benchmark",
    "run_eda_benchmark",
    "SecurityAudit",
    "run_security_audit",
    "compute_sql_accuracy",
    "compute_answer_accuracy",
]
