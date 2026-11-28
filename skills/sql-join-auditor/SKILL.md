---
name: sql-join-auditor
description: Profile the real cardinality behavior of supported equality joins against user-authorized CSV or Parquet files. Use for unexpected duplicate rows, inflated aggregates, or pre-merge SQL join review; do not use for non-equality joins, unavailable representative data, or general metric regression analysis.
---

# MetricTrace — SQL Join Auditor

Use this skill to examine an executed join's evidence, rather than guessing
from SQL text. It uses MetricTrace Lite's deterministic join-audit engine over
explicitly authorized CSV or Parquet files. It requires Python 3.11+ and
`metrictrace-lite`; it requires no AI key, account, Docker daemon, or network
connection.

## Activation and boundaries

Use when a SQL query has a direct equality `JOIN ... ON` condition and the
user needs to know whether actual input keys cause unmatched rows, duplicate
matches, or a potential aggregate-amplification risk. Use the SQL Regression
Guardian instead when the question is whether a metric value changed between
two definitions. Use Dataset Diff Inspector when the question is whether two
data versions differ.

The engine intentionally returns uncertainty for unsupported join forms,
including non-equality predicates and predicates it cannot extract safely. Do
not rewrite the SQL to manufacture support, infer cardinality from schema
names, or claim that a flagged risk proves a business error.

## Deterministic workflow

1. Obtain the exact SQL and a reviewed JSON manifest mapping every referenced
   logical table to an explicitly authorized CSV or Parquet file.
2. Validate unfamiliar SQL and inspect the declared schemas before execution.
   Stop if tables are absent, paths were not authorized, or the SQL needs an
   unsupported join interpretation.
3. Run the audit with bounded DuckDB limits. Retain the JSON report, including
   extracted joins, key profiles, unmatched row counts, joined row counts,
   aggregate context, uncertainty, and fingerprint.
4. For each supported join, distinguish observed duplicate groups from the
   engine's `potential_aggregate_amplification` assessment. Investigate the
   source data and intended grain before changing SQL.
5. Report unsupported shapes as uncertainty, not success. Preserve the exact
   SQL and manifest or immutable equivalents for reproducibility.

## Invocation

```bash
metrictrace join-audit \
  --dataset-manifest datasets.json \
  --sql-file candidate_metric.sql
```

`datasets.json` maps logical SQL table names to local files, for example:

```json
{"orders":"orders.csv","payments":"payments.parquet"}
```

The command emits structured JSON. Exit code `0` means the audit executed,
not that every join is safe. Exit code `2` represents invalid or unauthorized
inputs, `3` a policy/resource rejection, and `4` an execution failure.

## Supported execution modes

- Local CLI: validated on Windows with Python 3.11.
- Local MCP: `audit_local_sql_joins`, after setting
  `METRICTRACE_ALLOWED_DATA_DIRS` to authorized roots.
- Remote MetricTrace execution is not implemented for this skill.

## Security and error handling

Never inspect undeclared files, expand manifest access, upload data, or send
reports to an external service. The input manifest is the authorization
boundary. DuckDB resource limits reduce accidental resource use but do not
provide an operating-system sandbox. Return a structured command error as-is;
do not silently replace missing data, broaden time or memory limits, or treat
an unsupported join as a zero-risk result.

## Deterministic verification

An audit is reproducible only when it records the exact SQL, authorized
manifest, engine limits, extracted predicates, and output fingerprint.
`supported: false` or non-empty `uncertainty` blocks a conclusive join claim.
Re-run after any SQL, dataset, manifest, or limit changes.
