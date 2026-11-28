"""Deterministic SQL regression checks over identical approved datasets."""

from __future__ import annotations

import hashlib
import json
import time
from decimal import Decimal
from typing import Mapping

from metrictrace_sdk.core import validate_metric_sql
from metrictrace_sdk.local_replay import LocalReplayError, LocalReplayLimits, execute_local_scalar, normalize_datasets


class RegressionError(RuntimeError):
    """Stable error for invalid SQL regression configurations."""


def _decimal(value: str | None, name: str) -> Decimal | None:
    if value is None:
        return None
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise RegressionError(f"{name} must be a finite decimal value.") from exc
    if not result.is_finite() or result < 0:
        raise RegressionError(f"{name} must be a non-negative finite decimal value.")
    return result


def validate_regression_thresholds(
    max_absolute_difference: str | None, max_percent_difference: str | None
) -> None:
    """Validate policy thresholds without executing SQL or touching a dataset."""
    _decimal(max_absolute_difference, "max_absolute_difference")
    _decimal(max_percent_difference, "max_percent_difference")


def check_sql_regression(
    datasets: str | Mapping[str, str],
    baseline_sql: str,
    candidate_sql: str,
    *,
    max_absolute_difference: str | None = None,
    max_percent_difference: str | None = None,
    parameters: dict[str, object] | None = None,
    limits: LocalReplayLimits = LocalReplayLimits(),
    allowed_roots: tuple[str, ...] = (),
) -> dict:
    """Execute both definitions and evaluate explicit numeric regression gates."""
    try:
        paths = normalize_datasets(datasets, limits, allowed_roots)
        tables = set(paths)
        normalized_baseline = validate_metric_sql(baseline_sql, tables)
        normalized_candidate = validate_metric_sql(candidate_sql, tables)
    except (LocalReplayError, ValueError) as exc:
        raise RegressionError(str(exc)) from exc
    validate_regression_thresholds(max_absolute_difference, max_percent_difference)
    absolute_limit = _decimal(max_absolute_difference, "max_absolute_difference")
    percent_limit = _decimal(max_percent_difference, "max_percent_difference")
    started = time.perf_counter()
    try:
        baseline = execute_local_scalar(datasets, normalized_baseline, limits, parameters, allowed_roots)
        baseline_ms = round((time.perf_counter() - started) * 1000)
        candidate_started = time.perf_counter()
        candidate = execute_local_scalar(datasets, normalized_candidate, limits, parameters, allowed_roots)
        candidate_ms = round((time.perf_counter() - candidate_started) * 1000)
    except LocalReplayError as exc:
        raise RegressionError(str(exc)) from exc
    absolute_difference = abs(candidate - baseline)
    percent_difference = None if baseline == 0 else abs(candidate - baseline) / abs(baseline) * Decimal("100")
    gates = []
    if absolute_limit is not None:
        gates.append({"type": "absolute_difference", "limit": str(absolute_limit), "actual": str(absolute_difference), "status": "PASS" if absolute_difference <= absolute_limit else "FAIL"})
    if percent_limit is not None:
        if percent_difference is None:
            gates.append({"type": "percent_difference", "limit": str(percent_limit), "actual": None, "status": "ERROR", "message": "Percentage difference is undefined when baseline value is zero."})
        else:
            gates.append({"type": "percent_difference", "limit": str(percent_limit), "actual": str(percent_difference), "status": "PASS" if percent_difference <= percent_limit else "FAIL"})
    status = "PASS" if all(gate["status"] == "PASS" for gate in gates) else "FAIL"
    return {
        "status": status,
        "baseline": {"value": str(baseline), "duration_ms": baseline_ms, "normalized_sql": normalized_baseline},
        "candidate": {"value": str(candidate), "duration_ms": candidate_ms, "normalized_sql": normalized_candidate},
        "difference": {"absolute": str(absolute_difference), "percent": str(percent_difference) if percent_difference is not None else None},
        "gates": gates,
        "static_sql_changed": normalized_baseline != normalized_candidate,
        "fingerprint": hashlib.sha256(json.dumps({"datasets": {name: str(path) for name, path in paths.items()}, "baseline": normalized_baseline, "candidate": normalized_candidate, "parameters": parameters or {}, "absolute": str(absolute_limit), "percent": str(percent_limit)}, sort_keys=True).encode()).hexdigest(),
    }
