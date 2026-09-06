"""File ingestion: CSV/TSV/JSON/Excel/Parquet -> per-dataset SQLite file.

Each ingested dataset gets its own small SQLite database so downstream SQL
analysis (including the existing sqlglot-guarded executor) can operate on it
through a real connection string without touching user databases.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text

from app.data.descriptor import DatasetDescriptor
from app.data.profiler import fast_profile

SUPPORTED_EXTENSIONS = {".csv", ".tsv", ".json", ".xlsx", ".xls", ".parquet"}
MAX_ROWS = 1_000_000


class IngestionError(ValueError):
    pass


def detect_source_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise IngestionError(
            f"unsupported file type '{ext}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )
    return ext.lstrip(".")


def load_dataframe(filename: str, content: bytes) -> pd.DataFrame:
    ext = Path(filename).suffix.lower()
    import io

    try:
        if ext == ".csv":
            df = pd.read_csv(io.BytesIO(content))
        elif ext == ".tsv":
            df = pd.read_csv(io.BytesIO(content), sep="\t")
        elif ext == ".json":
            df = pd.read_json(io.BytesIO(content))
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(io.BytesIO(content))
        elif ext == ".parquet":
            df = pd.read_parquet(io.BytesIO(content))
        else:  # pragma: no cover - guarded by detect_source_type
            raise IngestionError(f"unsupported extension {ext}")
    except IngestionError:
        raise
    except Exception as exc:
        raise IngestionError(f"could not parse '{filename}': {exc}") from exc

    if df.empty:
        raise IngestionError(f"'{filename}' contains no rows")
    if len(df) > MAX_ROWS:
        raise IngestionError(f"'{filename}' has {len(df)} rows; limit is {MAX_ROWS}")
    # Normalize columns to string-safe names.
    df.columns = [str(c).strip().replace(" ", "_").lower()[:60] or f"col_{i}" for i, c in enumerate(df.columns)]
    return df


def persist_dataset(df: pd.DataFrame, uploads_dir: Path, dataset_id: str, table: str = "data") -> Path:
    uploads_dir.mkdir(parents=True, exist_ok=True)
    db_path = uploads_dir / f"{dataset_id}.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        df.to_sql(table, conn, if_exists="replace", index=False)
        conn.execute(text("SELECT 1"))
    engine.dispose()
    return db_path


def _sanitize_table_name(name: str) -> str:
    import re

    clean = re.sub(r"[^a-z0-9_]", "_", name.lower()).strip("_")
    return clean or "data"


def ingest_bytes(
    filename: str,
    content: bytes,
    *,
    dataset_id: str | None = None,
    uploads_dir: Path,
) -> tuple[DatasetDescriptor, Path, pd.DataFrame]:
    dataset_id = dataset_id or uuid.uuid4().hex
    ext = detect_source_type(filename)
    df = load_dataframe(filename, content)
    table = _sanitize_table_name(Path(filename).stem.lower()) or "data"
    db_path = persist_dataset(df, uploads_dir, dataset_id, table=table)
    descriptor = fast_profile(
        df,
        descriptor_id=dataset_id,
        name=Path(filename).stem,
        source=f"file:{ext}",
        table_name=table,
    )
    descriptor.size_bytes = len(content)
    return descriptor, db_path, df


def read_table(db_path: Path, table: str, limit: int | None = None) -> pd.DataFrame:
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        query = f'SELECT * FROM "{table}"'
        if limit:
            query += f" LIMIT {int(limit)}"
        return pd.read_sql_query(text(query), engine)
    finally:
        engine.dispose()


def table_summary(df: pd.DataFrame, limit: int = 5) -> dict[str, Any]:
    return {
        "columns": [str(c) for c in df.columns],
        "rows_preview": df.head(limit).replace({pd.NA: None}).astype(object).where(df.head(limit).notna(), None).to_dict("records"),
    }
