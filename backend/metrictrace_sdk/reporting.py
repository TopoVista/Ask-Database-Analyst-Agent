"""Canonical, shareable local replay reports; reports are integrity checked, not signed."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from metrictrace_sdk import __version__
from metrictrace_sdk.local_replay import (
    LocalReplayError,
    LocalReplayLimits,
    compare_dataset_schemas,
    inspect_datasets,
    normalize_datasets,
    run_local_four_way,
)

REPORT_SCHEMA_VERSION = "1.0"
DECISION_RECEIPT_SCHEMA_VERSION = "1.0"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def create_platform_decision_receipt(payload: dict) -> dict:
    """Attach an integrity digest to persisted platform evidence, never a signature."""
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0":
        raise ValueError("Platform decision receipts require schema version 1.0.")
    receipt = dict(payload)
    receipt["integrity_sha256"] = hashlib.sha256(_canonical(receipt)).hexdigest()
    return receipt


def verify_platform_decision_receipt(receipt: dict) -> dict[str, object]:
    """Verify receipt content integrity; this does not authenticate an author."""
    if not isinstance(receipt, dict):
        return {"valid": False, "integrity_valid": False, "missing_fields": ["receipt"]}
    required = {"schema_version", "replay_id", "cells", "attribution", "integrity_sha256"}
    missing = sorted(required - set(receipt))
    digest = receipt.get("integrity_sha256")
    unsigned = {key: value for key, value in receipt.items() if key != "integrity_sha256"}
    integrity_valid = isinstance(digest, str) and digest == hashlib.sha256(_canonical(unsigned)).hexdigest()
    attribution = receipt.get("attribution", {})
    return {
        "valid": not missing and integrity_valid and attribution.get("reconciles") is True,
        "integrity_valid": integrity_valid,
        "reconciliation_valid": attribution.get("reconciles") is True,
        "missing_fields": missing,
        "note": "SHA-256 checks receipt integrity; it is not an authenticated signature.",
    }


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dataset_identities(
    datasets: str | Mapping[str, str], limits, *, allowed_roots: tuple[str, ...] = ()
) -> dict[str, dict[str, object]]:
    """Use basenames only—reports should not disclose local absolute paths."""
    paths = normalize_datasets(datasets, limits, allowed_roots)
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
    import sqlglot

    dataset_evidence = {
        "old_datasets": dataset_identities(old_datasets, limits),
        "new_datasets": dataset_identities(new_datasets, limits),
    }
    definition_evidence = {
        "old_sql_sha256": hashlib.sha256(old_sql.encode("utf-8")).hexdigest(),
        "new_sql_sha256": hashlib.sha256(new_sql.encode("utf-8")).hexdigest(),
        "parameters": parameters or {},
    }
    report = {
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "metrictrace_version": __version__,
        "duckdb_version": duckdb.__version__,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs": {
            **dataset_evidence,
            **definition_evidence,
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
        "decision_receipt": {
            "schema_version": DECISION_RECEIPT_SCHEMA_VERSION,
            "scope": "local_file_replay",
            "dataset_version_identifiers": None,
            "evidence": {**dataset_evidence, **definition_evidence},
            "execution_engine": {"metrictrace_version": __version__, "duckdb_version": duckdb.__version__},
            "compiler": {"name": "sqlglot", "version": sqlglot.__version__, "dialect": "duckdb"},
            "contract_outcomes": None,
            "limitations": [
                "Local file replay has no persisted platform dataset-version identifiers.",
                "Contract outcomes are absent unless a separate contract evaluation is attached by the caller.",
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


def generate_investigation_report(report: dict) -> dict[str, object]:
    """Render an evidence-bounded investigation brief from a verified replay.

    This intentionally does not call an AI model.  Every finding points to a
    value already present in the integrity-checked report, so agent hosts can
    add their own narrative without being given unsupported causal claims.
    """
    verification = verify_report(report)
    if not verification["valid"]:
        raise ValueError("Investigation reports require a structurally complete, verified replay report.")
    attribution = report["replay"]["attribution"]
    compatibility = report["schemas"]["compatibility"]
    findings = [
        {
            "kind": kind,
            "value": attribution[key],
            "evidence_path": f"replay.attribution.{key}",
        }
        for kind, key in (
            ("observed_total_change", "total_change"),
            ("symmetric_data_contribution", "data_contribution"),
            ("symmetric_definition_contribution", "definition_contribution"),
            ("interaction_diagnostic", "interaction_effect"),
        )
    ]
    return {
        "schema_version": "1.0",
        "status": "VERIFIED",
        "report_integrity_sha256": report["integrity_sha256"],
        "verification": verification,
        "findings": findings,
        "schema_compatibility": {
            "compatible": compatibility.get("compatible"),
            "evidence_path": "schemas.compatibility",
        },
        "recommended_checks": [
            {
                "question": "Which declared data change explains the observed data contribution?",
                "evidence_boundary": "The receipt quantifies contribution but does not establish cause.",
            },
            {
                "question": "Does the interaction diagnostic warrant a segment-level replay?",
                "evidence_boundary": "The interaction is a numerical diagnostic, not an ownership finding.",
            },
        ],
        "limitations": [
            "Findings are deterministic restatements of the verified replay evidence.",
            "This report does not authenticate an author, prove source-system custody, or establish causality.",
            "No rows, local paths, credentials, or external AI services are included or contacted.",
        ],
    }


def _input_mismatches(
    expected: object, supplied: str | Mapping[str, str], limits: LocalReplayLimits,
    allowed_roots: tuple[str, ...], label: str,
) -> list[dict[str, str]]:
    if not isinstance(expected, dict):
        return [{"kind": "missing_receipt_evidence", "detail": f"Receipt has no {label} dataset manifest."}]
    try:
        observed = dataset_identities(supplied, limits, allowed_roots=allowed_roots)
    except (LocalReplayError, OSError) as exc:
        return [{"kind": "input_unavailable", "detail": f"{label} datasets could not be authorized/read: {exc}"}]
    mismatches: list[dict[str, str]] = []
    for name in sorted(set(expected) | set(observed)):
        if name not in expected:
            mismatches.append({"kind": "unexpected_dataset", "detail": f"{label} dataset {name!r} is not declared by the receipt."})
        elif name not in observed:
            mismatches.append({"kind": "missing_dataset", "detail": f"{label} dataset {name!r} is unavailable."})
        elif expected[name] != observed[name]:
            mismatches.append({"kind": "dataset_identity_mismatch", "detail": f"{label} dataset {name!r} hash or size differs from the receipt."})
    return mismatches


def reproduce_report(
    report: dict,
    old_datasets: str | Mapping[str, str],
    new_datasets: str | Mapping[str, str],
    old_sql: str,
    new_sql: str,
    *,
    limits: LocalReplayLimits = LocalReplayLimits(),
    parameters: dict | None = None,
    allowed_roots: tuple[str, ...] = (),
) -> dict[str, object]:
    """Re-execute an authorized local report and distinguish evidence failures.

    This checks supplied file identities and SQL hashes before execution. It is
    deliberately not a signature or custody/provenance system.
    """
    verification = verify_report(report)
    inputs = report.get("inputs") if isinstance(report, dict) else None
    result: dict[str, object] = {
        "structural_valid": not verification["missing_fields"] and verification["complete_cells"],
        "integrity_valid": verification["integrity_valid"],
        "reconciliation_valid": verification["reconciliation_valid"],
        "environment": {"metrictrace_version": __version__},
        "reexecution": {"status": "NOT_ATTEMPTED", "mismatches": []},
        "limitations": [
            "Reproduction confirms only the supplied local evidence and execution environment.",
            "It does not authenticate an author, establish custody, or prove source-system provenance.",
        ],
    }
    if not isinstance(inputs, dict):
        result["reexecution"] = {
            "status": "MISSING_EVIDENCE",
            "mismatches": [{"kind": "missing_receipt_evidence", "detail": "Receipt inputs are unavailable."}],
        }
        return result
    mismatches = _input_mismatches(inputs.get("old_datasets"), old_datasets, limits, allowed_roots, "old")
    mismatches.extend(_input_mismatches(inputs.get("new_datasets"), new_datasets, limits, allowed_roots, "new"))
    for label, sql in (("old_sql_sha256", old_sql), ("new_sql_sha256", new_sql)):
        if inputs.get(label) != hashlib.sha256(sql.encode("utf-8")).hexdigest():
            mismatches.append({"kind": "definition_hash_mismatch", "detail": f"Supplied {label.removesuffix('_sha256')} differs from the receipt."})
    if inputs.get("parameters", {}) != (parameters or {}):
        mismatches.append({"kind": "parameter_mismatch", "detail": "Supplied parameters differ from the receipt."})
    if mismatches:
        result["reexecution"] = {"status": "INPUT_MISMATCH", "mismatches": mismatches}
        return result
    try:
        replay = run_local_four_way(
            old_datasets, new_datasets, old_sql, new_sql, limits, parameters, allowed_roots=allowed_roots
        )
    except (LocalReplayError, ValueError) as exc:
        result["reexecution"] = {
            "status": "EXECUTION_FAILED",
            "mismatches": [{"kind": "execution_error", "detail": str(exc)}],
        }
        return result
    expected_replay = report.get("replay")
    if not isinstance(expected_replay, dict):
        result["reexecution"] = {
            "status": "MISSING_EVIDENCE",
            "mismatches": [{"kind": "missing_receipt_evidence", "detail": "Receipt replay evidence is unavailable."}],
        }
        return result
    replay_mismatches = []
    for field in ("cells", "attribution"):
        if expected_replay.get(field) != replay.get(field):
            replay_mismatches.append({"kind": "result_mismatch", "detail": f"Re-executed {field} differs from the receipt."})
    result["reexecution"] = {
        "status": "REPRODUCED" if not replay_mismatches else "RESULT_MISMATCH",
        "mismatches": replay_mismatches,
        "replay": replay,
    }
    return result


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
