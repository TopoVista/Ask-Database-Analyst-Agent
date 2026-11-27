from __future__ import annotations

from datetime import datetime, timezone
import json

from metrictrace_sdk.cli import main
from metrictrace_sdk.contracts import ERROR, FAIL, PASS, evaluate_contracts


def test_contracts_return_deterministic_evidence_and_fail_closed_for_mandatory_rules(tmp_path):
    orders = tmp_path / "orders.csv"
    payments = tmp_path / "payments.csv"
    now = datetime.now(timezone.utc).isoformat()
    orders.write_text(
        f"order_id,customer_id,amount,observed_at\n1,10,100,{now}\n2,20,-5,{now}\n3,99,10,{now}\n",
        encoding="utf-8",
    )
    payments.write_text("payment_id,order_id,amount\n1,1,100\n2,999,5\n", encoding="utf-8")
    contracts = [
        {"id": "columns", "type": "required_columns", "table": "orders", "columns": ["order_id", "amount"]},
        {"id": "schema", "type": "schema_type", "table": "orders", "column": "amount", "expected_type": "BIGINT"},
        {"id": "unique", "type": "primary_key_unique", "table": "orders", "columns": ["order_id"]},
        {"id": "nonnegative", "type": "non_negative", "table": "orders", "column": "amount"},
        {"id": "reference", "type": "referential_integrity", "table": "orders", "column": "customer_id", "reference_table": "payments", "reference_column": "payment_id"},
        {"id": "fresh", "type": "freshness", "table": "orders", "column": "observed_at", "max_age_seconds": 60},
        {"id": "absolute", "type": "absolute_change", "actual": "105", "baseline": "100", "max_change": "5"},
        {"id": "percent-zero", "type": "percentage_change", "actual": "5", "baseline": "0", "max_percent": "5", "severity": "warning"},
        {"id": "assert", "type": "sql_assertion", "sql": "SELECT COUNT(*) > 0 FROM orders"},
        {"id": "reconcile", "type": "cross_metric_reconciliation", "left_sql": "SELECT SUM(amount) FROM payments", "right_sql": "SELECT 105", "tolerance": "0"},
    ]

    report = evaluate_contracts({"orders": str(orders), "payments": str(payments)}, contracts)
    outcomes = {outcome["id"]: outcome for outcome in report["outcomes"]}

    assert outcomes["columns"]["status"] == PASS
    assert outcomes["schema"]["status"] == PASS
    assert outcomes["unique"]["status"] == PASS
    assert outcomes["nonnegative"]["status"] == FAIL
    assert outcomes["nonnegative"]["evidence"]["violating_rows"] == 1
    assert outcomes["reference"]["status"] == FAIL
    assert outcomes["fresh"]["status"] == PASS
    assert outcomes["absolute"]["status"] == PASS
    assert outcomes["percent-zero"]["status"] == ERROR
    assert outcomes["assert"]["status"] == PASS
    assert outcomes["reconcile"]["status"] == PASS
    assert report["summary"]["mandatory_passed"] is False


def test_missing_tables_are_not_evaluated_and_do_not_become_silent_passes(tmp_path):
    data = tmp_path / "orders.csv"
    data.write_text("order_id\n1\n", encoding="utf-8")

    report = evaluate_contracts(
        {"orders": str(data)},
        [{"id": "missing", "type": "non_null", "table": "payments", "column": "amount"}],
    )

    assert report["outcomes"][0]["status"] == "NOT_EVALUATED"
    assert report["summary"]["mandatory_passed"] is False


def test_contract_cli_returns_nonzero_for_a_mandatory_violation(tmp_path, capsys):
    dataset, contract_file, manifest = tmp_path / "orders.csv", tmp_path / "contracts.json", tmp_path / "manifest.json"
    dataset.write_text("order_id,amount\n1,-1\n", encoding="utf-8")
    manifest.write_text(json.dumps({"orders": dataset.name}), encoding="utf-8")
    contract_file.write_text(json.dumps([{"id": "positive", "type": "non_negative", "table": "orders", "column": "amount"}]), encoding="utf-8")

    assert main(["contracts-evaluate", "--dataset-manifest", str(manifest), "--contracts", str(contract_file)]) == 5
    body = json.loads(capsys.readouterr().out)
    assert body["ok"] is False
    assert body["contracts"]["outcomes"][0]["status"] == FAIL
