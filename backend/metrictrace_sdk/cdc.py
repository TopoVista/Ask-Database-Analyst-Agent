"""Deterministic validation for bounded PostgreSQL logical-decoding batches.

This module does not create replication slots, connect to PostgreSQL, or apply
row changes.  It verifies the ordering and acknowledgement evidence a caller
must preserve before a transport adapter durably advances an LSN checkpoint.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


class CdcError(ValueError):
    """Stable input-contract error for CDC batch validation."""


OPERATIONS = frozenset({"INSERT", "UPDATE", "DELETE"})


def parse_lsn(value: str) -> int:
    """Parse a PostgreSQL LSN formatted as hexadecimal `X/Y`."""
    if not isinstance(value, str) or value.count("/") != 1:
        raise CdcError("LSN must use PostgreSQL hexadecimal X/Y format.")
    high, low = value.split("/", 1)
    try:
        parsed = (int(high, 16) << 32) + int(low, 16)
    except ValueError as exc:
        raise CdcError("LSN must use PostgreSQL hexadecimal X/Y format.") from exc
    if parsed < 0:
        raise CdcError("LSN must be non-negative.")
    return parsed


def validate_cdc_batch(events: Iterable[dict[str, Any]], checkpoint_lsn: str | None = None) -> dict[str, Any]:
    """Validate one ordered, bounded CDC batch and return an acknowledgement.

    Duplicate event IDs are ignored only when their payload is identical. A
    batch may not go backwards from its durable checkpoint or reverse commit
    ordering. Callers persist `acknowledgement_lsn` only after durable event
    handling succeeds.
    """
    previous_lsn = parse_lsn(checkpoint_lsn) if checkpoint_lsn else None
    seen: dict[str, tuple[int, str, str | None]] = {}
    accepted: list[dict[str, Any]] = []
    duplicates = 0
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise CdcError(f"CDC event {index} must be an object.")
        event_id, operation, lsn = event.get("event_id"), event.get("operation"), event.get("commit_lsn")
        transaction_id = event.get("transaction_id")
        if not isinstance(event_id, str) or not event_id:
            raise CdcError(f"CDC event {index} requires a non-empty event_id.")
        if operation not in OPERATIONS:
            raise CdcError(f"CDC event {index} operation must be INSERT, UPDATE, or DELETE.")
        parsed_lsn = parse_lsn(lsn)
        if previous_lsn is not None and parsed_lsn < previous_lsn:
            raise CdcError("CDC commit LSN cannot move backwards from the checkpoint or prior event.")
        fingerprint = (parsed_lsn, operation, transaction_id if isinstance(transaction_id, str) else None)
        if event_id in seen:
            if seen[event_id] != fingerprint:
                raise CdcError("A duplicate CDC event_id has conflicting ordering metadata.")
            duplicates += 1
            continue
        seen[event_id] = fingerprint
        previous_lsn = parsed_lsn
        accepted.append({
            "event_id": event_id,
            "operation": operation,
            "commit_lsn": lsn.upper(),
            "transaction_id": transaction_id if isinstance(transaction_id, str) else None,
            "commit_order": len(accepted),
        })
    return {
        "schema_version": "1.0",
        "accepted_events": accepted,
        "accepted_count": len(accepted),
        "duplicate_count": duplicates,
        "acknowledgement_lsn": accepted[-1]["commit_lsn"] if accepted else checkpoint_lsn,
        "limitations": [
            "Validation does not create a replication slot, consume WAL, or apply row changes.",
            "Advance a durable LSN checkpoint only after downstream event handling is committed.",
        ],
    }
