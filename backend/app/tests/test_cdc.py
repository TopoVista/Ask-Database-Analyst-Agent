from __future__ import annotations

import json

import pytest

from metrictrace_sdk.cdc import CdcError, validate_cdc_batch
from metrictrace_sdk.cli import main


def test_cdc_batch_preserves_commit_order_deduplicates_and_acknowledges_latest_lsn(tmp_path, capsys):
    events = [
        {"event_id": "a", "operation": "INSERT", "commit_lsn": "0/10", "transaction_id": "tx-1"},
        {"event_id": "a", "operation": "INSERT", "commit_lsn": "0/10", "transaction_id": "tx-1"},
        {"event_id": "b", "operation": "UPDATE", "commit_lsn": "0/20", "transaction_id": "tx-2"},
    ]
    report = validate_cdc_batch(events, "0/8")
    assert report["accepted_count"] == 2
    assert report["duplicate_count"] == 1
    assert report["acknowledgement_lsn"] == "0/20"
    assert [event["commit_order"] for event in report["accepted_events"]] == [0, 1]

    event_file = tmp_path / "events.json"
    event_file.write_text(json.dumps(events), encoding="utf-8")
    assert main(["cdc-validate", "--events", str(event_file), "--checkpoint-lsn", "0/8"]) == 0
    assert json.loads(capsys.readouterr().out)["cdc"]["acknowledgement_lsn"] == "0/20"


def test_cdc_batch_rejects_lsn_regression_and_conflicting_duplicates():
    with pytest.raises(CdcError, match="cannot move backwards"):
        validate_cdc_batch([{"event_id": "a", "operation": "DELETE", "commit_lsn": "0/9"}], "0/A")
    with pytest.raises(CdcError, match="conflicting"):
        validate_cdc_batch([
            {"event_id": "a", "operation": "INSERT", "commit_lsn": "0/A"},
            {"event_id": "a", "operation": "UPDATE", "commit_lsn": "0/A"},
        ])
