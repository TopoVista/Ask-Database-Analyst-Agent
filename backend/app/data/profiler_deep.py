"""Deep profiling stage + shared profiler helpers.

Fast profile (app.data.profiler) always runs at ingestion. Deep profile
(correlations, outliers, duplicates, candidate keys) runs on demand and is
persisted back to the descriptor.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.data.descriptor import ColumnProfile, DatasetDescriptor


def deep_profile(df: pd.DataFrame, descriptor: DatasetDescriptor) -> DatasetDescriptor:
    numeric = df.select_dtypes(include=[np.number])
    if len(numeric.columns) >= 2:
        corr = numeric.corr(numeric_only=True)
        pairs = []
        cols = list(corr.columns)
        for i, a in enumerate(cols):
            for b in cols[i + 1:]:
                value = corr.loc[a, b]
                if pd.notna(value) and abs(value) > 0.5:
                    pairs.append({"a": a, "b": b, "correlation": round(float(value), 3)})
        descriptor.statistics["correlations"] = sorted(pairs, key=lambda p: -abs(p["correlation"]))[:20]

    outliers: dict[str, int] = {}
    for col in numeric.columns:
        series = numeric[col].dropna()
        if len(series) < 8:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        count = int(((series < lo) | (series > hi)).sum())
        if count:
            outliers[col] = count
    if outliers:
        descriptor.statistics["outliers"] = outliers

    duplicate_rows = int(df.duplicated().sum())
    if duplicate_rows:
        descriptor.statistics["duplicate_rows"] = duplicate_rows

    for col in descriptor.columns:
        if col.unique_count == descriptor.row_count and col.missing_count == 0:
            descriptor.relationships.append({"kind": "candidate_primary_key", "column": col.name})
            break

    descriptor.deep_profiled = True
    _quality_checks(df, descriptor)
    return descriptor


def _assign_column_groups(descriptor: DatasetDescriptor) -> None:
    for col in descriptor.columns:
        st = col.semantic_type
        if st == "temporal":
            descriptor.time_columns.append(col.name)
        elif st in ("geo_lat", "geo_lon"):
            descriptor.geo_columns.append(col.name)
        elif st == "text":
            descriptor.text_columns.append(col.name)
        elif st == "identifier":
            descriptor.identifier_columns.append(col.name)
        elif st == "measure":
            descriptor.measure_columns.append(col.name)
        elif st == "categorical":
            descriptor.categorical_columns.append(col.name)


def _basic_statistics(df: pd.DataFrame, descriptor: DatasetDescriptor) -> None:
    stats: dict[str, dict[str, float]] = {}
    for col in df.select_dtypes(include=[np.number]).columns:
        series = df[col].dropna()
        if series.empty:
            continue
        stats[col] = {
            "mean": round(float(series.mean()), 4),
            "std": round(float(series.std()), 4) if len(series) > 1 else 0.0,
            "min": float(series.min()),
            "max": float(series.max()),
            "median": round(float(series.median()), 4),
        }
    if stats:
        descriptor.statistics["numeric_summary"] = stats


def _quality_checks(df: pd.DataFrame, descriptor: DatasetDescriptor) -> None:
    report: dict[str, object] = {}
    high_missing = [
        {"column": c.name, "missing_pct": c.missing_pct}
        for c in descriptor.columns
        if c.missing_pct > 40
    ]
    if high_missing:
        report["high_missingness"] = high_missing
    constant = [c.name for c in descriptor.columns if c.unique_count <= 1 and descriptor.row_count > 1]
    if constant:
        report["constant_columns"] = constant
    total_missing_cells = int(df.isna().sum().sum())
    total_cells = df.size
    report["total_missing"] = total_missing_cells
    report["overall_completeness_pct"] = (
        round((1 - total_missing_cells / total_cells) * 100, 2) if total_cells else 100.0
    )
    descriptor.quality_report = report


def _infer_dataset_type(descriptor: DatasetDescriptor) -> None:
    if descriptor.time_columns and descriptor.measure_columns:
        descriptor.type = "time_series"
    elif descriptor.text_columns and not descriptor.measure_columns:
        descriptor.type = "text"
    elif descriptor.geo_columns:
        descriptor.type = "geospatial"
    else:
        descriptor.type = "tabular"

