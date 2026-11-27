from __future__ import annotations

import json

from metrictrace_sdk.cli import main
from metrictrace_sdk.regression import check_sql_regression


def test_regression_executes_both_definitions_and_applies_numeric_gates(tmp_path):
    data = tmp_path / "orders.csv"
    data.write_text("amount,status\n100,paid\n20,pending\n", encoding="utf-8")

    report = check_sql_regression(
        str(data),
        "SELECT SUM(amount) FROM source_data",
        "SELECT SUM(amount) FROM source_data WHERE status = 'paid'",
        max_absolute_difference="10",
        max_percent_difference="10",
    )

    assert report["status"] == "FAIL"
    assert report["baseline"]["value"] == "120"
    assert report["candidate"]["value"] == "100"
    assert report["difference"] == {"absolute": "20", "percent": "16.66666666666666666666666667"}
    assert {gate["status"] for gate in report["gates"]} == {"FAIL"}
    assert report["static_sql_changed"] is True


def test_regression_cli_has_machine_readable_nonzero_gate_failure(tmp_path, capsys):
    data = tmp_path / "orders.csv"
    data.write_text("amount\n10\n", encoding="utf-8")

    assert main([
        "regression-check", "--dataset", str(data),
        "--baseline-sql", "SELECT SUM(amount) FROM source_data",
        "--candidate-sql", "SELECT 0 FROM source_data LIMIT 1",
        "--max-absolute-difference", "1",
    ]) == 3
    body = json.loads(capsys.readouterr().out)
    assert body["ok"] is False
    assert body["regression"]["gates"][0]["status"] == "FAIL"
