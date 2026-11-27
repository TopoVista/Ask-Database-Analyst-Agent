---
name: historical-metric-debugger
description: Investigate a historical business-metric regression by executing MetricTrace's deterministic four-way SQL replay over explicitly authorized CSV or Parquet snapshots. Use for changed revenue, dashboard restatements, SQL-definition disputes, and data-versus-definition attribution; do not use when historical inputs cannot be supplied.
---

# MetricTrace — SQL & Data Regression Debugger

Use this skill to obtain evidence, not to estimate a result in prompt text. It supports local Lite CLI execution and an authenticated MetricTrace Platform API. Local mode requires Python 3.11+, `metrictrace-lite`, and files the user explicitly authorizes. It does not require an AI key, Docker, a hosted service, or network access.

## Workflow

1. Confirm the old and new datasets and old and new SQL definitions. Do not invent a missing historical snapshot, cell, parameter, or schema mapping.
2. For local work, ask for the minimum file authorization needed. Use a single `source_data` file or manifests mapping logical table names to approved CSV/Parquet files.
3. Validate SQL and inspect schemas before replay. Stop if definitions reference undeclared tables, schemas are not comparable, or a required column is missing.
4. Execute the actual A/B/C/D replay and save its JSON report. A is old data/old SQL, B old data/new SQL, C new data/old SQL, and D new data/new SQL.
5. Verify the report digest and numerical reconciliation. Explain the three-part data/definition/interaction decomposition and the symmetric Shapley allocations without double counting interaction.
6. State limitations: this is numerical attribution, not causal proof; report integrity is not author authentication; CSV inference can be unsuitable for sensitive financial types.

## Local invocation

```bash
metrictrace local-replay --old-dataset old.csv --new-dataset new.csv \
  --old-sql-file old.sql --new-sql-file new.sql --output replay.json
metrictrace verify-report --report replay.json
```

For multiple tables, provide an explicitly reviewed manifest such as `{"orders":"orders.csv","customers":"customers.csv"}` and use `--old-manifest` / `--new-manifest`. Run `metrictrace inspect` and `metrictrace validate-sql` first when files or SQL are unfamiliar.

## Security boundary

Never access a path that the user has not authorized. Never use generated SQL that invokes file readers, URLs, extension installation, attachments, shell execution, or undeclared tables. Do not upload rows, environment variables, tokens, or reports to external services. Failures and missing cells are failures—not zeroes. Process limits reduce accidental resource exhaustion but are not a hardened operating-system sandbox.

## Remote mode

Use the remote CLI only when the user has supplied authenticated tenant-scoped access and has explicitly authorized replay submission. Do not issue state-changing remote calls merely to explore.

## Error handling

Return the exact structured error category, identify the blocked input, and request the smallest corrective action. Do not retry a timeout with broader resource limits without user authorization. Do not claim compatibility or a successfully replayed result if execution did not complete.
