"""Staged dataset profiling.

Fast profile always runs at ingestion (cheap stats + semantic types).
Deep profile (correlations, outliers, duplicates, candidate keys) runs on
demand and is persisted back to the descriptor.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.data.descriptor import ColumnProfile, DatasetDescriptor
from app.data.profiler_deep import (
    _assign_column_groups,
    _basic_statistics,
    _infer_dataset_type,
    _quality_checks,
)
from app.data.semantic import infer_semantic_type


def _sample_values(series: pd.Series, n: int = 50) -> list[Any]:
    vals = series.dropna().head(n).tolist()
    out: list[Any] = []
    for v in vals:
        if isinstance(v, pd.Timestamp):
            out.append(v.isoformat())
        elif isinstance(v, np.integer):
            out.append(int(v))
        elif isinstance(v, np.floating):
            out.append(float(v))
        else:
            out.append(v if isinstance(v, (str, int, float, bool)) else str(v))
    return out


def fast_profile(df: pd.DataFrame, descriptor_id: str, name: str, source: str, table_name: str) -> DatasetDescriptor:
    columns: list[ColumnProfile] = []
    total = len(df)
    for col in df.columns:
        series = df[col]
        dtype = str(series.dtype)
        semantic = infer_semantic_type(str(col), dtype, _sample_values(series))
        missing = int(series.isna().sum())
        columns.append(
            ColumnProfile(
                name=str(col),
                dtype=dtype,
                semantic_type=semantic,
                missing_count=missing,
                missing_pct=round(missing / total * 100, 2) if total else 0.0,
                unique_count=int(series.nunique(dropna=True)),
            )
        )

    descriptor = DatasetDescriptor(
        id=descriptor_id,
        name=name,
        source=source,
        table_name=table_name,
        row_count=total,
        column_count=len(df.columns),
        columns=columns,
    )
    _assign_column_groups(descriptor)
    _basic_statistics(df, descriptor)
    _quality_checks(df, descriptor)
    _infer_dataset_type(descriptor)
    return descriptor
