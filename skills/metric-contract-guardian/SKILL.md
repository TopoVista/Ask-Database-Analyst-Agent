---
name: metric-contract-guardian
description: Evaluate declarative data and metric contracts over user-authorized local CSV or Parquet files. Use when explicit quality rules must produce deterministic evidence; do not use when no datasets or contract document can be supplied.
---

# MetricTrace — Metric Contract Guardian

Evaluate actual contract rules; never infer a PASS from descriptions, samples,
or a model's judgment. This skill uses the local `metrictrace contracts-evaluate`
command or `evaluate_local_contracts` MCP tool. It requires Python 3.11+ and
`metrictrace-lite`, authorized CSV/Parquet files, and a JSON contract document.
It needs no AI key, remote account, Docker, or network service.

## Activation and scope

Use when a user supplies business-quality rules such as required columns,
non-negative values, key uniqueness, freshness, referential integrity, or
cross-metric reconciliation. Do not invent a rule, baseline, type, or data
mapping. Local output is deterministic evidence for the supplied files, not a
claim about an unprovided production dataset.

## Workflow

1. Obtain a reviewed table manifest mapping logical table names to authorized
   CSV/Parquet files and a JSON contract document.
2. Confirm every table and column in the contract exists before interpreting
   outcomes. Missing prerequisites produce `NOT_EVALUATED`, never PASS.
3. Execute the evaluator. Retain the complete JSON output and fingerprint.
4. Treat mandatory (`severity: "error"`) outcomes as fail-closed: only PASS
   satisfies the mandatory gate. Warning outcomes remain visible but do not
   determine the mandatory verdict.
5. Report failed evidence, rule severity, and the smallest corrective action.
   Do not alter source data or contract policy without authorization.

## Contract document and command

```json
{
  "contracts": [
    {"id":"revenue-nonnegative","type":"non_negative","table":"orders","column":"revenue","severity":"error"},
    {"id":"order-key","type":"primary_key_unique","table":"orders","columns":["order_id"]}
  ]
}
```

```bash
metrictrace contracts-evaluate \
  --dataset-manifest datasets.json \
  --contracts contracts.json
```

Supported rules are required columns, schema type, non-null, minimum, maximum,
non-negative, primary-key uniqueness, absolute/percentage change, referential
integrity, freshness, bounded read-only SQL assertions, and cross-metric
reconciliation. Unsupported rule types return `ERROR`; they must not be
silently skipped.

## Modes and boundaries

- Local CLI: validated Windows Python 3.11 mode.
- Local MCP: `evaluate_local_contracts` after explicitly configuring
  `METRICTRACE_ALLOWED_DATA_DIRS`.
- Remote platform contract persistence/evaluation is not implemented. Do not
  claim remote compatibility or submit a state-changing request.

Never access paths outside user authorization. Do not use arbitrary Python,
write SQL, network functions, extensions, environment reads, or external
uploads. Resource limits reduce accidental exhaustion but are not a hardened
sandbox. Preserve exact structured errors and do not retry with wider limits
unless the user authorizes it.
