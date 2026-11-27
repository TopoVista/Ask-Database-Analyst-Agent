---
name: sql-safety-auditor
description: Validate read-only metric SQL against explicitly authorized logical tables. Use before local replay, regression testing, or contract SQL assertions; do not use it to rewrite a metric definition or approve database privileges.
---

# MetricTrace — SQL Safety Auditor

Use the implemented MetricTrace SQL validator as the authority for local
metric-query policy. It accepts one read-only SELECT/WITH query over declared
logical tables and rejects writes, multiple statements, external file readers,
URLs, extension installation, attachments, environment access, and undeclared
tables. It is a query-policy check, not a full database security audit.

## Workflow

1. Obtain the candidate SQL and the exact set of authorized logical table
   names from the reviewed local manifest.
2. Run the validator before any execution.
3. Return the normalized SQL only when validation succeeds. For failures,
   preserve the exact structured error and identify the prohibited construct.
4. Do not repair, rewrite, or execute invalid SQL. Ask for an approved metric
   definition or table manifest instead.

## Invocation

```bash
metrictrace validate-sql \
  --sql-file metric.sql \
  --tables orders,customers
```

For MCP use `validate_metric_sql` with the same explicit table allow-list.
Validation does not establish that SQL has the intended business meaning, will
return a scalar, or is affordable to execute; use replay/regression checks for
those questions.

## Security boundary

Never add a table to make a query pass. Never authorize filesystem paths,
network access, extensions, credentials, shell execution, writes, or database
mutations. Do not claim a query is safe for production merely because it meets
this Lite policy. Retain the original SQL and validation result as evidence.

## Execution modes

- Local CLI and local MCP only; no API key is required.
- Validated environment: Windows Python 3.11 with `metrictrace-lite`.
- Remote SQL validation and privilege inspection are not implemented.
