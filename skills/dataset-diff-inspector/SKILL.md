---
name: dataset-diff-inspector
description: Compare two user-authorized CSV or Parquet datasets with stable-key validation or explicit multiset semantics. Use for historical-versus-current data changes, inserted/deleted/modified records, and schema differences; do not use to infer row correspondence when no stable key exists.
---

# MetricTrace — Dataset Diff Inspector

Use this skill for deterministic evidence of how two authorized data files
differ. It invokes MetricTrace Lite's shared dataset-diff engine and requires
Python 3.11+ with `metrictrace-lite`. It is local-first: no AI key, hosted
account, Docker daemon, or network connection is needed.

## Activation and boundaries

Use when the user has an old and new CSV or Parquet dataset and needs schema
changes, inserted/deleted records, or field-level changes. A supplied stable
key makes record correspondence possible. Without one, the tool deliberately
uses multiset comparison and never presents a speculative row matching.

Do not use this skill for a SQL-definition regression (use SQL Regression
Guardian), for join grain analysis (use SQL Join Auditor), or when either
input has not been explicitly authorized. A duplicate or null stable key
makes key-based records non-comparable; report that result rather than
choosing an arbitrary match.

## Deterministic workflow

1. Confirm the old and new local paths and the smallest necessary file-access
   authorization. Identify candidate business keys only when their stability
   is known.
2. Inspect schemas if types or columns are unfamiliar. Do not coerce business
   keys silently or use row order as a key.
3. Run a bounded comparison. With keys, it validates nulls and duplicate key
   groups before reporting inserted, deleted, unchanged, and modified records.
   Without keys, it reports only multiset additions/removals and schema facts.
4. Preserve the JSON evidence, including schema changes, key-validation
   outcomes, pagination inputs, summaries, sample records, and fingerprint.
5. State whether output is key-comparable. A non-comparable result is useful
   evidence but is not a row-level diff.

## Invocation

```bash
metrictrace dataset-diff \
  --old-dataset before.parquet \
  --new-dataset after.parquet \
  --keys account_id,period \
  --limit 100
```

Omit `--keys` only when multiset semantics are intentional. Add
`--format markdown --output comparison.md` for a human-readable summary;
machine-readable JSON remains the authoritative evidence. Exit code `0` means
the comparison executed; exit code `2` means invalid input, `3` means a policy
or resource rejection, and `4` means execution failure.

## Supported execution modes

- Local CLI: validated on Windows with Python 3.11.
- Local MCP: `compare_local_datasets`, after configuring
  `METRICTRACE_ALLOWED_DATA_DIRS` for the approved roots.
- Remote MetricTrace execution and historical platform snapshots are not
  implemented for this skill.

## Security and error handling

Only use paths the user authorizes. Do not discover sibling files, upload
rows, loosen limits, or disclose environment variables. The engine's DuckDB
limits mitigate accidental resource use but are not an OS sandbox. Preserve
structured errors and request the smallest corrective input; do not retry a
failed key comparison in a weaker matching mode unless the user explicitly
requests a multiset comparison.

## Deterministic verification

A key-aware result is conclusive only when `summary.comparable` is true and
the same key list, source files, limits, offset, and evidence pagination are
recorded. A keyless report proves multiset counts only. Any changed file,
keys, or limits requires a fresh result.
