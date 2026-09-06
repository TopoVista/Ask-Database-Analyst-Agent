"""DatasetDescriptor: normalized metadata for any ingested dataset."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    semantic_type: str = "unknown"  # identifier|measure|temporal|categorical|text|geo_lat|geo_lon|boolean
    missing_count: int = 0
    missing_pct: float = 0.0
    unique_count: int = 0
    description: str = ""


@dataclass
class DatasetDescriptor:
    id: str
    name: str
    source: str  # "file:csv" | "file:excel" | "database" | ...
    type: str = "tabular"  # tabular|time_series|text|geospatial|multimodal
    schema_name: str = "main"
    table_name: str = ""
    row_count: int = 0
    column_count: int = 0
    size_bytes: int = 0
    columns: list[ColumnProfile] = field(default_factory=list)
    time_columns: list[str] = field(default_factory=list)
    geo_columns: list[str] = field(default_factory=list)
    text_columns: list[str] = field(default_factory=list)
    identifier_columns: list[str] = field(default_factory=list)
    measure_columns: list[str] = field(default_factory=list)
    categorical_columns: list[str] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)
    quality_report: dict[str, Any] = field(default_factory=dict)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    deep_profiled: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["columns"] = [c if isinstance(c, dict) else asdict(c) for c in self.columns]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DatasetDescriptor":
        """Reconstruct a descriptor, coercing serialized column dicts into
        :class:`ColumnProfile` objects so downstream code can use attributes."""
        columns = data.get("columns", [])
        if columns and isinstance(columns[0], dict):
            columns = [ColumnProfile(**c) for c in columns]
        data = {**data, "columns": columns}
        return cls(**data)
