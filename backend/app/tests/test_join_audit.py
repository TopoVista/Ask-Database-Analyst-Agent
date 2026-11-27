from __future__ import annotations

from metrictrace_sdk.join_audit import audit_sql_joins


def test_join_audit_profiles_actual_duplicate_keys_unmatched_rows_and_amplification(tmp_path):
    orders, payments = tmp_path / "orders.csv", tmp_path / "payments.csv"
    orders.write_text("order_id,amount\n1,100\n2,50\n3,25\n", encoding="utf-8")
    payments.write_text("payment_id,order_id\na,1\nb,1\nc,2\nd,99\n", encoding="utf-8")

    report = audit_sql_joins(
        {"orders": str(orders), "payments": str(payments)},
        "SELECT SUM(orders.amount) FROM orders JOIN payments ON orders.order_id = payments.order_id",
    )

    assert report["supported"] is True
    assert report["aggregations"] == ["SUM(orders.amount)"]
    join = report["joins"][0]
    assert join["joined_rows"] == 3
    assert join["unmatched_left_rows"] == 1
    assert join["unmatched_right_rows"] == 1
    assert join["right"]["profile"]["duplicate_key_groups"] == 1
    assert join["potential_aggregate_amplification"] is False


def test_join_audit_returns_uncertainty_for_non_equality_join_predicates(tmp_path):
    left, right = tmp_path / "left.csv", tmp_path / "right.csv"
    left.write_text("id\n1\n", encoding="utf-8")
    right.write_text("id\n1\n", encoding="utf-8")

    report = audit_sql_joins({"left_table": str(left), "right_table": str(right)}, "SELECT * FROM left_table JOIN right_table ON left_table.id < right_table.id")

    assert report["supported"] is False
    assert report["uncertainty"]
