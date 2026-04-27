from __future__ import annotations

from dataclasses import dataclass
import re

try:  # pragma: no cover - optional dependency
    import sqlglot
except Exception:  # pragma: no cover
    sqlglot = None


@dataclass
class ValidationResult:
    is_valid: bool
    reason: str = ""
    normalized_sql: str = ""


def _strip_sql(sql: str) -> str:
    text = sql.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("sql\n", "", 1).strip()
    return text.rstrip(";").strip()


def validate_sql(sql: str) -> ValidationResult:
    cleaned = _strip_sql(sql)
    forbidden = ["INSERT ", "UPDATE ", "DELETE ", "DROP ", "TRUNCATE ", "ALTER ", "CREATE ", "GRANT ", "REVOKE "]
    upper = cleaned.upper()
    if any(keyword in upper for keyword in forbidden):
        return ValidationResult(False, "Only SELECT queries are allowed.", cleaned)
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        return ValidationResult(False, "Query must start with SELECT or WITH.", cleaned)
    if sqlglot is not None:
        try:
            parsed = sqlglot.parse_one(cleaned, dialect="postgres")
            if parsed is None:
                return ValidationResult(False, "Unable to parse SQL.", cleaned)
        except Exception as exc:
            return ValidationResult(False, f"Invalid SQL syntax: {exc}", cleaned)
    return ValidationResult(True, normalized_sql=cleaned)

