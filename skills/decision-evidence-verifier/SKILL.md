---
name: decision-evidence-verifier
description: Verify the integrity and numerical reconciliation of a supplied MetricTrace local replay report. Use when a decision cites a replay report; do not use to reconstruct missing evidence or authenticate a report's author.
---

# MetricTrace — Decision Evidence Verifier

Verify a supplied MetricTrace replay report with the implemented report digest
and four-cell reconciliation verifier. This establishes whether the report has
the expected internal integrity and arithmetic evidence; it does not prove
human authorship, source-system provenance, business causality, or approval
authority.

## Workflow

1. Obtain the complete JSON report file. Do not recreate it from a summary,
   chat transcript, screenshot, or the current state of a source database.
2. Run the verifier and preserve its machine-readable result.
3. Require both integrity and numerical reconciliation to be valid before
   treating the supplied replay output as internally consistent.
4. Separately state any unverified links: source file custody, identity,
   decision approval, remote dataset-version lineage, and business context.

## Invocation

```bash
metrictrace verify-report --report replay.json
```

For MCP use `verify_replay_report` with the complete report object. A digest
mismatch or missing cell is a verification failure; never replace it with zero
or infer a passing result.

## Boundaries

The verifier requires no API key and is validated locally on Windows Python
3.11 with `metrictrace-lite`. Do not upload reports, inspect unapproved paths,
modify a decision record, claim blockchain-style provenance, or claim remote
decision-receipt support. Platform decision receipts and persisted approval
lineage are not implemented.
