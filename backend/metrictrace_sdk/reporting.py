"""Canonical, shareable local replay reports; reports are integrity checked, not signed."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from metrictrace_sdk import __version__
from metrictrace_sdk.local_replay import (
    compare_dataset_schemas,
    inspect_datasets,
    normalize_datasets,
)

REPORT_SCHEMA_VERSION = "1.0"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dataset_identities(datasets: str | Mapping[str, str], limits) -> dict[str, dict[str, object]]:
    """Use basenames only—reports should not disclose local absolute paths."""
    paths = normalize_datasets(datasets, limits)
    return {
        name: {
            "file_name": path.name,
            "sha256": _sha256_path(path),
            "size_bytes": path.stat().st_size,
        }
        for name, path in sorted(paths.items())
    }


def create_report(
    old_datasets,
    new_datasets,
    old_sql: str,
    new_sql: str,
    replay: dict,
    limits,
    parameters: dict | None = None,
    duration_ms: int = 0,
) -> dict:
    """Build the deterministic core report; timestamp is the only non-deterministic evidence field."""
    import duckdb

    old_schema = inspect_datasets(old_datasets, limits)
    new_schema = inspect_datasets(new_datasets, limits)
    report = {
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "metrictrace_version": __version__,
        "duckdb_version": duckdb.__version__,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs": {
            "old_datasets": dataset_identities(old_datasets, limits),
            "new_datasets": dataset_identities(new_datasets, limits),
            "old_sql_sha256": hashlib.sha256(old_sql.encode("utf-8")).hexdigest(),
            "new_sql_sha256": hashlib.sha256(new_sql.encode("utf-8")).hexdigest(),
            "parameters": parameters or {},
        },
        "schemas": {
            "old": old_schema,
            "new": new_schema,
            "compatibility": compare_dataset_schemas(old_schema, new_schema),
        },
        "replay": replay,
        "execution": {
            "duration_ms": duration_ms,
            "limits": {
                "timeout_seconds": limits.timeout_seconds,
                "memory_limit": limits.memory_limit,
                "threads": limits.threads,
                "max_input_bytes": limits.max_input_bytes,
            },
            "warnings": [
                "Integrity confirms report contents, not author identity or re-execution against source files."
            ],
        },
    }
    report["integrity_sha256"] = hashlib.sha256(_canonical(report)).hexdigest()
    return report


def verify_report(report: dict) -> dict[str, object]:
    """Check structure, canonical digest, and mathematical reconciliation without rerunning SQL."""
    required = {
        "report_schema_version",
        "inputs",
        "schemas",
        "replay",
        "execution",
        "integrity_sha256",
    }
    missing = sorted(required - set(report))
    supplied = report.get("integrity_sha256", "")
    unsigned = {key: value for key, value in report.items() if key != "integrity_sha256"}
    integrity_valid = (
        isinstance(supplied, str) and supplied == hashlib.sha256(_canonical(unsigned)).hexdigest()
    )
    attribution = report.get("replay", {}).get("attribution", {})
    reconciliation_valid = attribution.get("reconciles") is True
    cells = report.get("replay", {}).get("cells", {})
    complete_cells = set(cells) == {
        "old_data_old_definition",
        "old_data_new_definition",
        "new_data_old_definition",
        "new_data_new_definition",
    }
    return {
        "valid": not missing and integrity_valid and reconciliation_valid and complete_cells,
        "missing_fields": missing,
        "integrity_valid": integrity_valid,
        "reconciliation_valid": reconciliation_valid,
        "complete_cells": complete_cells,
        "note": "Verification does not authenticate an author or rerun the original datasets.",
    }


def markdown_report(report: dict) -> str:
    replay, attribution = report["replay"], report["replay"]["attribution"]
    cells = replay["cells"]
    compatibility = report["schemas"]["compatibility"]
    lines = [
        "# MetricTrace historical metric replay",
        "",
        "## Executive summary",
        "",
        f"The metric changed by **{attribution['total_change']}**. The three-part decomposition reconciles: **{attribution['reconciles']}**.",
        "",
        "## Four-way replay",
        "",
        "| Cell | Value |",
        "| --- | ---: |",
        *[f"| {name} | {value} |" for name, value in cells.items()],
        "",
        "## Attribution",
        "",
        "| Component | Value |",
        "| --- | ---: |",
        f"| Data main effect | {attribution['data_effect']} |",
        f"| Definition main effect | {attribution['definition_effect']} |",
        f"| Interaction diagnostic | {attribution['interaction_effect']} |",
        f"| Symmetric data contribution | {attribution['data_contribution']} |",
        f"| Symmetric definition contribution | {attribution['definition_contribution']} |",
        "",
        "## Schema compatibility",
        "",
        f"Compatible: **{compatibility['compatible']}**. Rename detection is disabled unless mappings are explicitly supplied.",
        "",
        "## Evidence and limitations",
        "",
        f"Report integrity SHA-256: `{report['integrity_sha256']}`.",
        "The calculation is numerical attribution, not causal inference. Integrity checking does not authenticate an author or re-execute the original datasets.",
        "",
        "## Suggested investigation",
        "",
        "Review the data and definition contributions separately, then inspect the interaction before assigning ownership.",
        "",
    ]
    return "\n".join(lines)
