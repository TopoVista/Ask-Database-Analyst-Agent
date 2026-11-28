from __future__ import annotations

import json

import duckdb
import pytest

from metrictrace_sdk.cli import main
from metrictrace_sdk.local_replay import (
    LocalReplayError,
    LocalReplayLimits,
    compare_dataset_schemas,
    execute_local_scalar,
    inspect_datasets,
    run_local_four_way,
)
from metrictrace_sdk.reporting import create_report, reproduce_report, verify_report


def test_lite_multi_table_replay_and_report_integrity(tmp_path):
    old_orders = tmp_path / "old-orders.csv"
    new_orders = tmp_path / "new-orders.csv"
    customers = tmp_path / "customers.csv"
    old_orders.write_text("customer_id,amount\n1,100\n2,50\n", encoding="utf-8")
    new_orders.write_text("customer_id,amount\n1,80\n2,50\n", encoding="utf-8")
    customers.write_text("customer_id,segment\n1,paid\n2,trial\n", encoding="utf-8")
    old = {"orders": str(old_orders), "customers": str(customers)}
    new = {"orders": str(new_orders), "customers": str(customers)}
    old_sql = "SELECT SUM(amount) FROM orders JOIN customers USING (customer_id)"
    new_sql = "SELECT SUM(amount) FROM orders JOIN customers USING (customer_id) WHERE segment = 'paid'"
    limits = LocalReplayLimits(timeout_seconds=15)
    replay = run_local_four_way(old, new, old_sql, new_sql, limits)
    assert replay["cells"] == {
        "old_data_old_definition": "150",
        "old_data_new_definition": "100",
        "new_data_old_definition": "130",
        "new_data_new_definition": "80",
    }
    report = create_report(old, new, old_sql, new_sql, replay, limits)
    receipt = report["decision_receipt"]
    assert receipt["scope"] == "local_file_replay"
    assert receipt["dataset_version_identifiers"] is None
    assert receipt["compiler"]["name"] == "sqlglot"
    assert verify_report(report)["valid"] is True
    tampered = json.loads(json.dumps(report))
    tampered["replay"]["cells"]["new_data_new_definition"] = "81"
    assert verify_report(tampered)["integrity_valid"] is False


def test_report_reproduction_checks_exact_evidence_before_rerunning(tmp_path):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    old.write_text("amount\n10\n", encoding="utf-8")
    new.write_text("amount\n8\n", encoding="utf-8")
    limits = LocalReplayLimits(timeout_seconds=15)
    old_sql = new_sql = "SELECT SUM(amount) FROM source_data"
    report = create_report(
        str(old), str(new), old_sql, new_sql,
        run_local_four_way(str(old), str(new), old_sql, new_sql, limits), limits,
    )

    reproduced = reproduce_report(report, str(old), str(new), old_sql, new_sql, limits=limits)
    assert reproduced["structural_valid"] is True
    assert reproduced["integrity_valid"] is True
    assert reproduced["reexecution"]["status"] == "REPRODUCED"

    new.write_text("amount\n9\n", encoding="utf-8")
    mismatched = reproduce_report(report, str(old), str(new), old_sql, new_sql, limits=limits)
    assert mismatched["reexecution"]["status"] == "INPUT_MISMATCH"
    assert mismatched["reexecution"]["mismatches"][0]["kind"] == "dataset_identity_mismatch"


def test_report_reproduction_cli_returns_structured_success(tmp_path, capsys):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    report_path = tmp_path / "report.json"
    old.write_text("amount\n10\n", encoding="utf-8")
    new.write_text("amount\n8\n", encoding="utf-8")
    sql = "SELECT SUM(amount) FROM source_data"
    limits = LocalReplayLimits(timeout_seconds=15)
    report_path.write_text(
        json.dumps(
            create_report(
                str(old), str(new), sql, sql,
                run_local_four_way(str(old), str(new), sql, sql, limits), limits,
            )
        ),
        encoding="utf-8",
    )

    assert main([
        "reproduce-report", "--report", str(report_path), "--old-dataset", str(old),
        "--new-dataset", str(new), "--old-sql", sql, "--new-sql", sql,
    ]) == 0
    assert json.loads(capsys.readouterr().out)["reproduction"]["reexecution"]["status"] == "REPRODUCED"


def test_lite_blocks_undeclared_tables_and_file_functions(tmp_path):
    data = tmp_path / "data.csv"
    data.write_text("amount\n1\n", encoding="utf-8")
    with pytest.raises(LocalReplayError, match="explicitly authorized"):
        run_local_four_way(str(data), str(data), "SELECT SUM(amount) FROM other", "SELECT SUM(amount) FROM source_data")
    with pytest.raises(LocalReplayError, match="external files"):
        run_local_four_way(str(data), str(data), "SELECT * FROM read_csv_auto('secret.csv')", "SELECT SUM(amount) FROM source_data")


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT http_get('https://example.invalid') FROM source_data",
        "SELECT env('HOME') FROM source_data",
        "SELECT load_extension('httpfs') FROM source_data",
    ],
)
def test_lite_blocks_network_environment_and_extension_functions(tmp_path, sql):
    data = tmp_path / "data.csv"
    data.write_text("amount\n1\n", encoding="utf-8")
    with pytest.raises(LocalReplayError, match="external files"):
        execute_local_scalar(str(data), sql)


def test_lite_schema_diagnostics_do_not_invent_renames(tmp_path):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    old.write_text("amount\n1\n", encoding="utf-8")
    new.write_text("revenue\n1\n", encoding="utf-8")
    result = compare_dataset_schemas(inspect_datasets(str(old)), inspect_datasets(str(new)))
    assert result["compatible"] is False
    assert result["rename_detection"] == "disabled_without_explicit_mapping"


def test_lite_replays_parquet_inputs(tmp_path):
    old = tmp_path / "old.parquet"
    new = tmp_path / "new.parquet"
    connection = duckdb.connect(":memory:")
    try:
        connection.execute(f"COPY (SELECT 10 AS amount) TO '{old.as_posix()}' (FORMAT PARQUET)")
        connection.execute(f"COPY (SELECT 8 AS amount) TO '{new.as_posix()}' (FORMAT PARQUET)")
    finally:
        connection.close()
    replay = run_local_four_way(str(old), str(new), "SELECT SUM(amount) FROM source_data", "SELECT SUM(amount) FROM source_data")
    assert replay["cells"]["old_data_old_definition"] == "10"
    assert replay["cells"]["new_data_new_definition"] == "8"


def test_lite_enforces_size_timeout_and_nonfinite_boundaries(tmp_path):
    data = tmp_path / "data.csv"
    data.write_text("amount\n1\n", encoding="utf-8")
    with pytest.raises(LocalReplayError, match="input limit"):
        execute_local_scalar(str(data), "SELECT SUM(amount) FROM source_data", LocalReplayLimits(max_input_bytes=1))
    with pytest.raises(LocalReplayError, match="non-finite"):
        execute_local_scalar(str(data), "SELECT CAST('NaN' AS DOUBLE) FROM source_data")
    with pytest.raises(LocalReplayError, match="wall-clock"):
        execute_local_scalar(
            str(data), "SELECT SUM(amount) FROM source_data",
            LocalReplayLimits(timeout_seconds=0.01),
        )


def test_lite_resolves_symlinks_before_authorization(tmp_path):
    approved = tmp_path / "approved"
    approved.mkdir()
    outside = tmp_path / "outside.csv"
    outside.write_text("amount\n1\n", encoding="utf-8")
    linked = approved / "linked.csv"
    try:
        linked.symlink_to(outside)
    except OSError:
        pytest.skip("Symlink creation is not permitted on this Windows host.")
    with pytest.raises(LocalReplayError, match="outside the authorized"):
        execute_local_scalar(
            str(linked), "SELECT SUM(amount) FROM source_data", allowed_roots=(str(approved),)
        )
