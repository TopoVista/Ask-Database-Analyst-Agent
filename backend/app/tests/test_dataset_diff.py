from __future__ import annotations

import json

from metrictrace_sdk.cli import main
from metrictrace_sdk.dataset_diff import compare_datasets


def _write(path, rows: str) -> str:
    path.write_text(rows, encoding="utf-8")
    return str(path)


def test_stable_key_diff_reports_insertions_deletions_modifications_and_evidence(tmp_path):
    old = _write(tmp_path / "old.csv", "id,amount,status\n1,10,paid\n2,20,paid\n3,30,paid\n")
    new = _write(tmp_path / "new.csv", "id,amount,status\n1,12,paid\n3,30,paid\n4,40,pending\n")

    report = compare_datasets(old, new, key_columns=["id"])

    assert report["summary"] == {
        "mode": "stable_key", "comparable": True, "inserted": 1, "deleted": 1, "modified": 1, "unchanged": 1,
    }
    by_key = {row["key"]["id"]: row for row in report["records"]}
    assert by_key[1]["changed_columns"] == ["amount"]
    assert by_key[1]["old"] == {"amount": 10, "status": "paid"}
    assert by_key[1]["new"] == {"amount": 12, "status": "paid"}
    assert by_key[2]["kind"] == "deleted"
    assert by_key[4]["kind"] == "inserted"
    json.dumps(report)


def test_duplicate_or_null_keys_fail_closed_without_row_matching(tmp_path):
    old = _write(tmp_path / "old.csv", "id,value\n1,a\n1,b\n,c\n")
    new = _write(tmp_path / "new.csv", "id,value\n1,a\n2,b\n3,c\n")

    report = compare_datasets(old, new, key_columns=["id"])

    assert report["summary"]["comparable"] is False
    assert report["records"] == []
    assert report["key_validation"]["old_data"] == {"duplicate_key_groups": 1, "null_key_rows": 1}


def test_keyless_comparison_is_explicit_multiset_not_false_row_matching(tmp_path):
    old = _write(tmp_path / "old.csv", "value\na\na\nb\n")
    new = _write(tmp_path / "new.csv", "value\na\nb\nb\n")

    report = compare_datasets(old, new)

    assert report["summary"]["mode"] == "multiset"
    assert report["summary"]["inserted"] == 1
    assert report["summary"]["deleted"] == 1
    assert report["records"] == []


def test_dataset_diff_cli_returns_machine_readable_evidence(tmp_path, capsys):
    old = _write(tmp_path / "old.csv", "id,value\n1,before\n")
    new = _write(tmp_path / "new.csv", "id,value\n1,after\n")

    assert main(["dataset-diff", "--old-dataset", old, "--new-dataset", new, "--keys", "id"]) == 0
    body = json.loads(capsys.readouterr().out)

    assert body["ok"] is True
    assert body["comparison"]["records"][0]["changed_columns"] == ["value"]
