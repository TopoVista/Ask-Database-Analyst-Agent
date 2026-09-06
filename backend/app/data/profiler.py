"""Staged dataset profiling — pure Python, no pandas/numpy.

Fast profile always runs at ingestion (cheap stats + semantic types).
Deep profile (correlations, outliers, duplicates) runs on demand.
"""

from __future__ import annotations

import math
import statistics
from typing import Any

from app.data.descriptor import ColumnProfile, DatasetDescriptor
from app.data.profiler_deep import (
    _assign_column_groups,
    _basic_statistics,
    _infer_dataset_type,
    _quality_checks,
)
from app.data.semantic import infer_semantic_type


def _coerce_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _sample_values(col: str, rows: list[dict], n: int = 50) -> list[Any]:
    out: list[Any] = []
    for row in rows:
        v = row.get(col)
        if v is None or v == "":
            continue
        out.append(v if isinstance(v, (str, int, float, bool)) else str(v))
        if len(out) >= n:
            break
    return out


def fast_profile(
    columns: list[str],
    rows: list[dict],
    *,
    descriptor_id: str,
    name: str,
    source: str,
    table_name: str,
) -> DatasetDescriptor:
    total = len(rows)
    col_profiles: list[ColumnProfile] = []

    for col in columns:
        vals = [row.get(col) for row in rows]
        missing = sum(1 for v in vals if v is None or v == "")
        non_null = [v for v in vals if v is not None and v != ""]
        unique_count = len(set(str(v) for v in non_null))

        # Infer dtype
        numeric_vals = [_coerce_float(v) for v in non_null]
        all_numeric = all(v is not None for v in numeric_vals) and bool(numeric_vals)
        dtype = "float64" if all_numeric else "object"

        sample = _sample_values(col, rows)
        semantic = infer_semantic_type(col, dtype, sample)

        col_profiles.append(
            ColumnProfile(
                name=col,
                dtype=dtype,
                semantic_type=semantic,
                missing_count=missing,
                missing_pct=round(missing / total * 100, 2) if total else 0.0,
                unique_count=unique_count,
            )
        )

    descriptor = DatasetDescriptor(
        id=descriptor_id,
        name=name,
        source=source,
        table_name=table_name,
        row_count=total,
        column_count=len(columns),
        columns=col_profiles,
    )
    _assign_column_groups(descriptor)
    _basic_statistics(columns, rows, descriptor)
    _quality_checks(columns, rows, descriptor)
    _infer_dataset_type(descriptor)
    return descriptor
