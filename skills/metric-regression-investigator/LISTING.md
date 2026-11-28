# MetricTrace — SQL Regression Guardian

An evidence-backed local SQL metric regression checker for approved CSV and
Parquet datasets. It executes baseline and candidate SQL against the same file
and returns stable JSON with numeric differences, explicit gate results, and a
reproducibility fingerprint.

## Buyer-facing disclosure

- Version: release candidate 0.2.0
- Execution model: local-first standalone Python script
- Supported formats: CSV and Parquet
- AI API key required: no
- Validated environment: Windows, Python 3.11
- Dependencies installed by buyer: `duckdb==1.1.3`, `sqlglot==25.31.4`

Use it when you have two SQL definitions and an approved representative data
file. The skill does not access the network, modify source data, inspect
undeclared paths, or decide whether a business change should be accepted.
