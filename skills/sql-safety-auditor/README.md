# MetricTrace — SQL Safety Auditor

This premium skill material invokes the MIT-licensed MetricTrace SQL validator.
Install `metrictrace-lite` in Windows Python 3.11, copy this directory to an
agent host that supports `SKILL.md`, and pass an explicit logical-table list.
No API key is required.

Run `python -m pytest app/tests/test_metrictrace_lite.py -q` from the backend
development tree to verify the shared SQL-policy engine.

The original instructional material is commercial material; see
`COMMERCIAL_NOTICE.md`. The shared engine remains MIT licensed.
