---
name: metric-definition-reviewer
description: Review baseline and candidate metric SQL for policy compatibility and observed semantic change on authorized representative data. Use before proposing a metric-definition change; do not use when representative data or either definition is unavailable.
---

# MetricTrace — Metric Definition Reviewer

Review two metric definitions in two layers: deterministic SQL-policy validity,
then observed output differences on the same authorized files. A textual SQL
diff is structural evidence only; it does not prove a changed metric result.
The local workflow needs Python 3.11+, `metrictrace-lite`, CSV/Parquet input,
and explicit file authorization. It does not require an AI key or hosted
MetricTrace service.

## Workflow

1. Obtain baseline and candidate SQL, their expected unit/currency/parameter
   assumptions, and a reviewed dataset or table manifest.
2. Validate each query with the precise logical table allow-list. Stop on
   unsafe or undeclared references; do not silently rewrite the definition.
3. Run `metrictrace regression-check` against identical data with explicit
   absolute or percentage thresholds. Preserve its JSON output and fingerprint.
4. Report both values, the normalized SQL, static SQL change, observed
   difference, gate results, and any known coverage limitation.
5. Recommend investigation only from observed evidence. Do not promote, roll
   back, edit, or publish a definition; platform promotion gates are not
   implemented in local mode.

## Invocation

```bash
metrictrace validate-sql --sql-file baseline.sql --tables orders
metrictrace validate-sql --sql-file candidate.sql --tables orders
metrictrace regression-check --dataset orders.csv \
  --baseline-sql-file baseline.sql --candidate-sql-file candidate.sql \
  --max-absolute-difference 0
```

For multiple tables, use `--manifest datasets.json`. A zero baseline makes a
percentage gate undefined; use an absolute threshold or return the explicit
gate error.

## Execution and security boundaries

Local CLI and `check_local_sql_regression` MCP are supported on validated
Windows Python 3.11. Remote platform definition comparison is not implemented.
Never access undeclared files, add tables to make SQL pass, use a generated
query, widen limits, send data externally, or claim branch protection. The
result applies only to the exact definitions, parameters, files, and limits in
the retained fingerprint.
