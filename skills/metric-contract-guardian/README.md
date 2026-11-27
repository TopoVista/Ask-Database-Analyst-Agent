# MetricTrace — Metric Contract Guardian

Premium local agent-skill material for deterministic data-contract evaluation.

## Install and validate

Install `metrictrace-lite` in a validated Windows Python 3.11 environment, copy
this directory into an agent host that reads `SKILL.md`, and provide authorized
CSV/Parquet files plus a JSON contract document. No API key is required.

Run `python -m pytest app/tests/test_contracts.py -q` from the backend source
tree to validate the shared engine in a development checkout.

## License

The MetricTrace shared engine is MIT licensed. The original instructional and
marketplace material in this directory is commercial material; see
`COMMERCIAL_NOTICE.md`.
