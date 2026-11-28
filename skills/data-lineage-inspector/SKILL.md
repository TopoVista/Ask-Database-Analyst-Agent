---
name: data-lineage-inspector
description: Inspect static SQL dependencies, CTEs, output expressions, and schema-surface changes for explicitly authorized tables. Use for metric dependency review or pre-change impact analysis; do not use as proof of runtime, row-level, or dynamic-SQL lineage.
---

# MetricTrace — Schema & Lineage Inspector

Use this skill to obtain static dependency evidence from read-only MetricTrace
SQL. It invokes the shared deterministic `metrictrace` CLI rather than
inventing data flow in prompt text. Local use requires Python 3.11+ and
`metrictrace-lite`; it has no AI-key, hosted-account, Docker, or network
requirement.

## Activation and boundaries

Use for a metric-definition review where the user needs to identify declared
source tables, common table expressions, output expressions, transformations,
or static dependency changes between two SQL definitions. Require an explicit
table allow-list. This is not a runtime execution plan, a row-level lineage
system, database-catalog discovery, or proof of schema compatibility.

Do not use this skill to compare metric values (use SQL Regression Guardian),
to identify changed records (use Dataset Diff Inspector), or to audit actual
join cardinality (use SQL Join Auditor). It rejects writes, external readers,
dynamic file access, and undeclared tables. It reports uncertainty instead of
claiming exact lineage for star projections, unqualified columns, derived
relations, or ambiguous aliases.

## Deterministic workflow

1. Obtain one or two exact SQL definitions and the smallest correct list of
   authorized logical tables. Do not expand that list merely to satisfy a
   parse error.
2. Run static inspection for one definition. Retain normalized SQL, source
   tables, CTE dependency context, output expressions, source-column
   references, transformations, uncertainty, and fingerprint.
3. For a proposed change, compare baseline and candidate definitions. Treat
   added or removed source tables/output names as static schema-surface
   evidence, not proof that every runtime result changes.
4. Review every uncertainty record before presenting a conclusive statement.
   Request schema or execution evidence when static analysis cannot resolve a
   dependency.
5. Preserve the exact SQL, allow-list, engine version, and output fingerprint
   for reproduction.

## Invocation

```bash
metrictrace lineage-inspect \
  --sql-file metric.sql \
  --tables orders,customers

metrictrace lineage-compare \
  --baseline-sql-file metric_before.sql \
  --candidate-sql-file metric_after.sql \
  --tables orders,customers
```

The command emits structured JSON. Exit code `0` means analysis completed;
exit code `2` indicates invalid inputs, `3` a policy/resource rejection, and
exit code `4` an execution failure. A completion result with uncertainty is
not a complete lineage proof.

## Supported execution modes

- Local CLI: validated on Windows with Python 3.11.
- Local MCP: `inspect_sql_lineage`; it requires no local file access because
  static SQL inspection uses only SQL text and an explicit allow-list.
- Remote MetricTrace lineage inspection, database-catalog ingestion, and
  persisted cross-version lineage are not implemented.

## Security and error handling

Do not read datasets, database catalogs, sibling files, environment values, or
network resources. The table allow-list is a strict declaration boundary, not
a discovery hint. Return structured errors unchanged; never modify SQL or
weaken authorization in order to obtain a report.

## Deterministic verification

A static result is reproducible only for the same SQL text, authorized table
list, and engine version. Confirm the output fingerprint and review
`uncertainty` before relying on it. Dynamic SQL or changes to any supplied
definition require a new inspection.
