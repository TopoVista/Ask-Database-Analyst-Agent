---
name: decision-evidence-verifier
description: Verify a MetricTrace replay report's structure, canonical integrity digest, arithmetic reconciliation, and, when exact authorized evidence is available, deterministically reproduce it. Use when a decision cites a MetricTrace report; do not use to authenticate an author or reconstruct missing evidence.
---

# MetricTrace - Decision Evidence Verifier

Use this skill to assess a supplied MetricTrace local replay report in
separate, explicit stages. It invokes the shared deterministic CLI; it never
declares that a digest is a signature or provenance proof. Local use needs
Python 3.11+, `metrictrace-lite`, and, for reproduction, the exact authorized
CSV/Parquet evidence and SQL. No AI API key, hosted service, Docker daemon,
or network connection is required.

## Activation and boundaries

Use when a decision, review, or incident record cites a complete MetricTrace
replay JSON report. First verify its report structure, canonical integrity
digest, and four-cell attribution reconciliation. If the user also supplies
the exact historical files, definitions, and parameters, reproduce the result
after checking their hashes against the receipt.

Do not use this skill to recreate missing data, estimate a report from a
screenshot, infer chain of custody, authenticate a person, or approve a
decision. A report can be structurally valid without integrity validity, and
integrity validity does not establish who created it or whether source data
was authoritative.

## Deterministic workflow

1. Obtain the complete JSON report. Run integrity verification first and
   preserve its JSON result.
2. State the independent verdicts: structural completeness, integrity digest,
   and numerical reconciliation. Do not collapse a failure into one vague
   "invalid" statement.
3. Ask for historical input only when reproduction is needed: old/new
   authorized dataset manifests, old/new SQL, and parameters. Do not discover
   files outside the user’s declared paths.
4. Run reproduction. It compares each dataset file hash and size, SQL hashes,
   and parameters before it executes the four replay cells.
5. Report `REPRODUCED`, `INPUT_MISMATCH`, `MISSING_EVIDENCE`,
   `RESULT_MISMATCH`, or `EXECUTION_FAILED` exactly. A hash mismatch blocks
   execution instead of producing a misleading comparison.

## Invocation

```bash
metrictrace verify-report --report replay.json

metrictrace reproduce-report --report replay.json \
  --old-dataset old.csv --new-dataset new.csv \
  --old-sql-file old.sql --new-sql-file new.sql
```

For multiple tables, use explicitly reviewed `--old-manifest` and
`--new-manifest` files. The commands emit structured JSON. `verify-report`
uses exit code `0` only for a valid digest/reconciliation result;
`reproduce-report` uses exit code `0` only for `REPRODUCED`.

## Supported execution modes

- Local CLI: validated on Windows with Python 3.11.
- Local MCP: `verify_replay_report` validates a supplied report object.
  Reproduction through MCP is not implemented because it requires an explicit
  local file/SQL authorization workflow.
- Remote platform decision receipts, signed receipts, and persisted approval
  lineage are not implemented.

## Security and error handling

Never upload reports, files, SQL, tokens, or environment values. Access only
paths explicitly supplied by the user and retain the configured resource
limits. Do not modify a report to make it verify, widen limits on retry, or
replace missing cells with zero. A SHA-256 integrity digest is not a
cryptographic signature and does not authenticate an author.

## Deterministic verification

A reproduction is valid only if the receipt is structurally complete,
integrity-valid, reconciled, and the re-execution status is `REPRODUCED`.
Changes to a file, SQL text, parameters, resource limits, or engine version
require a fresh report and verification.
