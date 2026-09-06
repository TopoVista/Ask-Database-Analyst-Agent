"""Pydantic schemas for dataset ingestion and profiling API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ColumnProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    dtype: str
    semantic_type: str
    missing_count: int = 0
    missing_pct: float = 0.0
    unique_count: int = 0
    description: str = ""


class DatasetDescriptorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    source: str
    type: str = "tabular"
    table_name: str = ""
    row_count: int = 0
    column_count: int = 0
    size_bytes: int = 0
    columns: list[ColumnProfileRead] = []
    time_columns: list[str] = []
    geo_columns: list[str] = []
    text_columns: list[str] = []
    identifier_columns: list[str] = []
    measure_columns: list[str] = []
    categorical_columns: list[str] = []
    statistics: dict[str, Any] = {}
    quality_report: dict[str, Any] = {}
    relationships: list[dict[str, Any]] = []
    deep_profiled: bool = False


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    filename: str
    source_type: str
    row_count: int
    column_count: int
    created_at: datetime
    descriptor: DatasetDescriptorRead | None = None


class DatasetListResponse(BaseModel):
    datasets: list[DatasetRead]
    total: int


class TablePreviewResponse(BaseModel):
    dataset_id: str
    table_name: str
    columns: list[str]
    rows_preview: list[dict[str, Any]]

