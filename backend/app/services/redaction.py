"""PII / sensitive-data redaction helpers for LLM-bound payloads.

Row values retrieved from a user's database may contain personally
identifiable information (names, emails, phone numbers, addresses, etc.).
Before those rows are serialized into an LLM prompt (which may be sent to an
external API), we mask sensitive columns and truncate very long free-text
values. This reduces the risk of leaking raw PII to a hosted model while still
preserving the analytical signal (numbers, categories) the insight agents need.

All functions are pure and deterministic; whether they actually run is gated by
``settings.redact_pii_in_prompts`` via the ``mask_*`` convenience wrappers.
"""

from __future__ import annotations

import re
from typing import Any

from app.config import get_settings

# Max number of characters kept for a single string value in an LLM payload.
# Long free-text columns (notes, comments, descriptions) can embed arbitrary
# user content (including PII), so we truncate them before they reach the model.
MAX_STRING_LENGTH = 200

MASK = "[REDACTED]"

# Column-name tokens that signal a personally-identifiable or secret-bearing
# field. Kept intentionally narrow so analytic-safe columns such as
# ``product_name``, ``order_id``, or ``account_status`` are *not* masked.
_PII_TOKENS = {
    "email",
    "mail",
    "phone",
    "telephone",
    "mobile",
    "cell",
    "address",
    "ssn",
    "social",
    "security",
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "cvv",
    "cvc",
    "card",
    "credit",
    "iban",
    "routing",
    "dob",
    "birth",
    "birthdate",
    "birthday",
    "national",
    "license",
    "passport",
    "driver",
    "drivers",
}

# Qualifiers that, when preceding a trailing "name" token, identify a person's
# name (as opposed to e.g. ``product_name`` or ``table_name``).
_NAME_QUALIFIERS = {
    "first",
    "last",
    "middle",
    "full",
    "customer",
    "client",
    "user",
    "person",
    "employee",
    "member",
    "contact",
}

_COLUMN_SPLIT_RE = re.compile(r"[_\-.\s]+")


def _column_tokens(column: Any) -> list[str]:
    if not column:
        return []
    return [part for part in _COLUMN_SPLIT_RE.split(str(column).strip().lower()) if part]


def is_sensitive_column(column: Any) -> bool:
    tokens = _column_tokens(column)
    if not tokens:
        return False
    # Person-name style columns: "name", "customer_name", "first_name".
    if tokens[-1] == "name" and (len(tokens) == 1 or tokens[-2] in _NAME_QUALIFIERS):
        return True
    # "account" is only sensitive when it holds an identifier (number/no/id/iban),
    # so analytic columns like account_status or account_type are preserved.
    if "account" in tokens and len(tokens) >= 2 and tokens[-1] in {"number", "no", "id", "iban"}:
        return True
    return any(token in _PII_TOKENS for token in tokens)


def redact_value(value: Any) -> Any:
    """Truncate very long free-text values; leave numbers and booleans intact."""
    if isinstance(value, str) and len(value) > MAX_STRING_LENGTH:
        return value[: MAX_STRING_LENGTH - 1] + "…"
    return value


def redact_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: (MASK if is_sensitive_column(key) else redact_value(value))
        for key, value in row.items()
    }


def redact_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [redact_row(row) for row in rows]


def redact_query_results(query_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Redact nested row payloads inside pipeline query-result dicts."""
    redacted: list[dict[str, Any]] = []
    for result in query_results:
        item = dict(result)
        for key in ("rows", "sample"):
            value = item.get(key)
            if isinstance(value, list):
                item[key] = redact_rows(value)
        redacted.append(item)
    return redacted


def mask_pii_in_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Redact rows unless PII redaction is disabled via settings."""
    if not get_settings().redact_pii_in_prompts:
        return rows
    return redact_rows(rows)


def mask_pii_in_query_results(query_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Redact query-result payloads unless PII redaction is disabled via settings."""
    if not get_settings().redact_pii_in_prompts:
        return query_results
    return redact_query_results(query_results)