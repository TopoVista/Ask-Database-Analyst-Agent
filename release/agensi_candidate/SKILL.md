---
name: historical-metric-debugger
description: Execute an evidence-backed four-way SQL replay over user-authorized historical CSV or Parquet snapshots to determine whether a metric changed because of data, SQL logic, or their interaction.
summary: Deterministically replay two metric definitions across two retained datasets.
version: 0.1.0
tags: [metrics, sql, data-quality, debugging]
---

# MetricTrace — SQL & Data Regression Debugger

Use this skill only when the user supplies or explicitly authorizes two retained historical dataset versions and two SQL definition files. It does not retrieve missing history, upload data, or infer results.

## Before execution

Confirm the two datasets, two SQL files, and each directory the user authorizes. Explain that the runner needs local Python 3.11+, `duckdb==1.1.3`, and `sqlglot==25.31.4`; request authorization before installing dependencies. Do not assume that an agent host supports Python or dependency installation.

## Execute

Run the included script directly from its temporary skill folder. It is intentionally self-contained and does not import this repository or a wheel.

```bash
python scripts/run_replay.py --old-dataset /approved/old.csv --new-dataset /approved/new.csv \
  --old-sql-file /approved/old.sql --new-sql-file /approved/new.sql \
  --allow-root /approved
```

Interpret A/B/C/D exactly as returned. Verify that all four cells completed and that `reconciles` is true before reporting data, definition, interaction, and symmetric contributions.

## Boundaries

Never fabricate old data, results, schema mappings, or causality. Never treat a failed cell as zero. The script permits only authorized CSV/Parquet paths beneath `--allow-root`, approved logical tables, and read-only SQL; it blocks external file readers, URLs, extensions, attachments, and undeclared tables. It provides process and DuckDB limits but is not an operating-system sandbox.

If Python/dependencies are unavailable or the host forbids execution, report that limitation rather than simulating a replay. For multi-table or report-verification workflows, use the installed MetricTrace Lite package outside this marketplace delivery.
