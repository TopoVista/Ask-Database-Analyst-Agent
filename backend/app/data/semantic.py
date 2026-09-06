"""Semantic type inference for columns.

Heuristic, dependency-light: combines dtype, name patterns, and value
inspection. This feeds SQL generation, chart selection, and analysis routing.
"""

from __future__ import annotations

import re
from typing import Any

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", re.IGNORECASE)
_LAT_RE = re.compile(r"^-?(?:[0-8]?\d|90)(?:\.\d+)?$")
_LON_RE = re.compile(r"^-?(?:\d{1,2}|1[0-7]\d|180)(?:\.\d+)?$")
_MONEY_NAME = re.compile(r"(revenue|sales|price|amount|cost|profit|salary|income|spend|payment|total|fee|budget)", re.I)
_ID_NAME = re.compile(r"(_id$|^id$|uuid|guid|_key$|_code$)", re.I)
_DATE_NAME = re.compile(r"(date|time|month|year|day|week|quarter|timestamp|period|created|updated)", re.I)
_TEXT_NAME = re.compile(r"(desc|description|comment|note|review|message|text|body|title|summary|transcript|content)", re.I)
_GEO_NAME = re.compile(r"(lat|latitude|lon|lng|longitude|coord)", re.I)


def infer_semantic_type(name: str, dtype: str, values: list[Any]) -> str:
    """Infer one of: identifier, measure, temporal, categorical, text,
    geo_lat, geo_lon, boolean, unknown."""
    non_null = [v for v in values if v is not None]
    if not non_null:
        return "unknown"

    dtype_l = dtype.lower()
    if dtype_l == "bool":
        return "boolean"

    strings = [str(v) for v in non_null[:200]]
    lower_name = name.lower()

    # Identifier columns are identified by name pattern, regardless of dtype.
    # This covers both numeric auto-increment IDs and string-based IDs (e.g.
    # "customer_id" with values like "ID_001").
    if _ID_NAME.search(lower_name):
        return "identifier"

    if _GEO_NAME.search(lower_name):
        numeric = _numeric_ratio(strings)
        if numeric > 0.9:
            if "lat" in lower_name:
                if all(_LAT_RE.match(s) for s in strings):
                    return "geo_lat"
            else:
                if all(_LON_RE.match(s) for s in strings):
                    return "geo_lon"

    if _DATE_NAME.search(lower_name):
        if dtype_l.startswith("datetime") or _looks_like_dates(strings):
            return "temporal"
        if dtype_l.startswith(("int", "float")) and re.search(r"(year|month|quarter|day|week)", lower_name):
            return "temporal"

    if dtype_l.startswith(("int", "float")):
        if _ID_NAME.search(lower_name):
            return "identifier"
        if _MONEY_NAME.search(lower_name):
            return "measure"
        if _looks_like_ids(strings):
            return "identifier"
        return "measure"

    # Email columns are PII-bearing text, not identifiers.
    if strings and _EMAIL_RE.match(strings[0]) and all(_EMAIL_RE.match(s) for s in strings):
        return "text"

    if _TEXT_NAME.search(lower_name):
        avg_len = sum(len(s) for s in strings) / len(strings)
        if avg_len > 40 or any(len(s) > 120 for s in strings):
            return "text"

    unique = set(strings)
    if len(unique) <= max(20, len(strings) // 2):
        return "categorical"
    return "text"


def _numeric_ratio(strings: list[str]) -> float:
    ok = 0
    for s in strings:
        try:
            float(s)
            ok += 1
        except ValueError:
            pass
    return ok / len(strings) if strings else 0.0


def _looks_like_ids(strings: list[str]) -> bool:
    if len(set(strings)) != len(strings):
        return False
    try:
        nums = [float(s) for s in strings]
    except ValueError:
        return False
    return all(n == int(n) and n >= 0 for n in nums) and max(nums) > len(strings)


def _looks_like_dates(strings: list[str]) -> bool:
    from datetime import datetime

    date_formats = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d", "%d-%m-%Y", "%m/%d/%Y", "%Y-%m", "%b %Y", "%B %Y"]
    checked = 0
    hits = 0
    for s in strings[:50]:
        for fmt in date_formats:
            try:
                datetime.strptime(s, fmt)
                hits += 1
                break
            except ValueError:
                continue
        checked += 1
    return checked > 0 and hits / checked > 0.8
