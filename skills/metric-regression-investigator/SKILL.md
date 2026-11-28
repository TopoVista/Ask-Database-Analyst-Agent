---
name: metric-regression-investigator
description: Execute an evidence-backed SQL metric regression check over user-authorized CSV or Parquet files. Use when reviewing a baseline and candidate metric definition before merge; do not use when approved representative data or both definitions are unavailable.
---

# MetricTrace — SQL Regression Guardian

Use this skill to reproduce a claimed SQL metric regression. It executes the
baseline and candidate definitions against the same explicitly authorized
local files; it does not infer semantic impact from a text diff. It requires
Python 3.11+, the included standalone runner, DuckDB, SQLGlot, and CSV or
Parquet inputs. It requires no AI API key, hosted MetricTrace account, Docker
daemon, or network service.

## Activation and boundaries

Use for a pull-request review, pre-merge check, or investigation where both
SQL definitions and a representative approved dataset can be supplied. Do not
claim a result for unavailable history, unapproved paths, missing tables, or
failed execution. This is a local semantic regression check, not a branch
protection rule or proof that a business change is incorrect.

Do not use it to discover files outside those the user authorizes. Do not
modify SQL, datasets, a database, a pull request, or a production metric.

## Deterministic workflow

1. Obtain one baseline SQL definition, one candidate definition, and one
   approved CSV or Parquet file. The runner exposes that file as `source_data`.
2. Inspect schemas and validate both definitions when they are unfamiliar.
   Stop when a definition references an undeclared table or unsafe file/network
   function.
3. Select explicit absolute and/or percentage gates. Treat a zero baseline as
   undefined for a percentage gate; use an absolute gate or record the error.
4. Execute the check and retain its JSON output, which contains both observed
   values, durations, normalized SQL, exact differences, gate outcomes, and a
   reproducibility fingerprint.
5. Report whether the gates passed. Separate the observed numerical change
   from any judgment about whether the definition should be promoted.

## Invocation

```bash
python scripts/run_regression.py \
  --dataset orders.csv \
  --baseline-sql-file metric_before.sql \
  --candidate-sql-file metric_after.sql \
  --allow-root . \
  --max-absolute-difference 100 \
  --max-percent-difference 2.5
```

The standalone commercial runner intentionally supports one explicitly
authorized source file. SQL must refer to it as `source_data`; multi-table
manifests and remote execution are not supported in this distribution.

Exit code `0` means all explicit gates passed. Exit code `3` means a gate
failed; `2` means invalid input; `4` means execution failed. Preserve the JSON
result rather than translating a failure into an unsupported conclusion.

## Supported execution modes

- Standalone local Python script: validated on Windows Python 3.11 with
  `duckdb==1.1.3` and `sqlglot==25.31.4` installed by the buyer.
- Agent hosts that can run local Python and read `SKILL.md` may invoke the
  script. Do not claim MCP, remote, CI-hosted, Linux, or macOS compatibility.

## Error handling and security

Return the command's structured error unchanged along with the blocked input.
Do not retry with larger time, memory, or file-access limits unless the user
explicitly authorizes that change. DuckDB limits and subprocess termination
reduce accidental resource consumption; they are not an operating-system
sandbox. Never send rows, environment values, tokens, or reports to external
services.

## Deterministic verification

The result is valid only when both definitions ran successfully against the
same declared dataset manifest and every configured gate is `PASS`. Verify the
fingerprint and retain the source SQL/files or their immutable equivalents.
Changing SQL, parameters, files, limits, or manifest makes it a new check.
