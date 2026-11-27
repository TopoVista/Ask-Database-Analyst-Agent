# MetricTrace — Decision Evidence Verifier

Install `metrictrace-lite` on Windows Python 3.11, copy this directory into an
agent host that supports `SKILL.md`, and provide the complete replay JSON
report. No API key is required.

Run `python -m pytest app/tests/test_metrictrace_lite.py -q` from the backend
source tree to verify replay-report integrity behavior.

The shared verifier is MIT licensed. Original instructional material in this
directory is commercial material; see `COMMERCIAL_NOTICE.md`.
