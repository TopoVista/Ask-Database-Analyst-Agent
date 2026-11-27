# MetricTrace — SQL Regression Guardian

Commercial skill material for local deterministic SQL regression review.

## Install

Install MetricTrace Lite in a Python 3.11 environment:

```bash
pip install metrictrace-lite
```

Copy this skill directory into an agent host that supports `SKILL.md`, then
provide explicitly authorized CSV/Parquet inputs and SQL files. No API key is
required. Only Windows Python 3.11 has been validated.

## Validation

The engine is covered by `backend/app/tests/test_regression.py` and the MCP
protocol suite. Run `python -m pytest app/tests/test_regression.py -q` from
the backend directory after installing development dependencies.

## License

The shared MetricTrace engine is MIT licensed. This original premium skill
material is separately licensed; see `COMMERCIAL_NOTICE.md`.
