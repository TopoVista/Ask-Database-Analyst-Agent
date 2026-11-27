from __future__ import annotations

import json

import pytest

from metrictrace_sdk.cli import main
from metrictrace_sdk.lineage import LineageError, compare_sql_lineage, inspect_sql_lineage


def test_static_lineage_tracks_authorized_base_tables_ctes_outputs_and_transformations():
    report = inspect_sql_lineage(
        """
        WITH paid AS (
          SELECT o.customer_id, o.amount
          FROM orders o
          WHERE o.status = 'paid'
        )
        SELECT customer_id, SUM(amount) AS revenue
        FROM paid
        GROUP BY customer_id
        """,
        ["orders"],
    )

    assert report["source_tables"] == ["orders"]
    assert report["common_table_expressions"][0]["name"] == "paid"
    assert report["common_table_expressions"][0]["source_tables"] == ["orders"]
    assert [column["name"] for column in report["output_columns"]] == ["customer_id", "revenue"]
    assert report["output_columns"][1]["transformations"] == ["SUM"]
    assert report["fingerprint"]


def test_lineage_rejects_unapproved_and_external_input_sql():
    with pytest.raises(LineageError, match="explicitly authorized"):
        inspect_sql_lineage("SELECT * FROM secret_orders", ["orders"])
    with pytest.raises(LineageError, match="external files"):
        inspect_sql_lineage("SELECT * FROM read_csv_auto('secret.csv')", ["orders"])


def test_lineage_comparison_reports_static_schema_surface_changes_and_cli_json(capsys):
    report = compare_sql_lineage(
        "SELECT id, amount FROM orders",
        "SELECT id, amount, tax FROM orders JOIN taxes ON orders.id = taxes.order_id",
        ["orders", "taxes"],
    )

    assert report["change"]["source_tables"]["added"] == ["taxes"]
    assert report["change"]["output_columns"]["added"] == ["tax"]
    assert main(["lineage-inspect", "--sql", "SELECT id FROM orders", "--tables", "orders"]) == 0
    body = json.loads(capsys.readouterr().out)
    assert body["ok"] is True
    assert body["lineage"]["source_tables"] == ["orders"]
