from __future__ import annotations

from app.services.redaction import (
    is_sensitive_column,
    mask_pii_in_query_results,
    redact_query_results,
    redact_row,
    redact_rows,
)


def test_sensitive_column_detection():
    assert is_sensitive_column("customer_name")
    assert is_sensitive_column("first_name")
    assert is_sensitive_column("email")
    assert is_sensitive_column("phone_number")
    assert is_sensitive_column("address")
    assert is_sensitive_column("account_number")
    assert is_sensitive_column("SSN")


def test_analytic_safe_columns_are_not_sensitive():
    # These must NOT be masked so analytical quality is preserved.
    assert not is_sensitive_column("product_name")
    assert not is_sensitive_column("order_id")
    assert not is_sensitive_column("table_name")
    assert not is_sensitive_column("foreign_key")
    assert not is_sensitive_column("account_status")
    assert not is_sensitive_column("amount")


def test_redact_row_masks_pii_and_preserves_safe_values():
    row = {
        "customer_name": "Alice Smith",
        "email": "alice@example.com",
        "phone_number": "555-0100",
        "product_name": "Widget",
        "region": "West",
        "amount": 123.45,
        "is_active": True,
    }
    out = redact_row(row)
    assert out["customer_name"] == "[REDACTED]"
    assert out["email"] == "[REDACTED]"
    assert out["phone_number"] == "[REDACTED]"
    assert out["product_name"] == "Widget"
    assert out["region"] == "West"
    assert out["amount"] == 123.45
    assert out["is_active"] is True


def test_redact_row_truncates_long_free_text():
    row = {"note": "x" * 500, "id": 42}
    out = redact_row(row)
    assert out["id"] == 42
    assert out["note"] != row["note"]
    assert len(out["note"]) <= 200


def test_redact_rows_preserves_row_count_and_order():
    rows = [
        {"customer_name": "A", "amount": 1},
        {"customer_name": "B", "amount": 2},
    ]
    out = redact_rows(rows)
    assert [r["amount"] for r in out] == [1, 2]
    assert all(r["customer_name"] == "[REDACTED]" for r in out)


def test_redact_query_results_nested_rows():
    results = [
        {"task_id": "T1", "rows": [{"email": "a@b.com", "revenue": 10}]},
        {"task_id": "T2", "sample": [{"address": "123 Main", "orders": 3}]},
    ]
    out = redact_query_results(results)
    assert out[0]["rows"][0]["email"] == "[REDACTED]"
    assert out[0]["rows"][0]["revenue"] == 10
    assert out[1]["sample"][0]["address"] == "[REDACTED]"
    assert out[1]["task_id"] == "T2"


def test_mask_pii_in_query_results_returns_same_shape():
    # Gated by settings; assert structural behavior, not exact masking value.
    results = [{"task_id": "T1", "rows": [{"email": "x@y.z"}]}]
    out = mask_pii_in_query_results(results)
    assert isinstance(out, list)
    assert len(out) == 1
    assert out[0]["task_id"] == "T1"
    assert "rows" in out[0]