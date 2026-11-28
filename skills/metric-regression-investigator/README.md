# MetricTrace — SQL Regression Guardian

Commercial skill material for local deterministic SQL regression review.

## Install

In a Windows Python 3.11 environment, install the two declared dependencies:

```bash
pip install -r requirements.txt
```

Copy this skill directory into an agent host that supports `SKILL.md`, then
run `scripts/run_regression.py` with explicit CSV/Parquet input, SQL file, and
`--allow-root` paths. SQL refers to the one approved dataset as `source_data`.
No API key is required. Only Windows Python 3.11 has been validated.

The runner is generated from MetricTrace's shared deterministic core by
`release/build_sql_regression_guardian.py`; do not edit it directly.

## Validation

The generated standalone runner is validated from a temporary extraction
directory. In the repository, run `python -m pytest app/tests/test_regression.py
app/tests/test_sql_regression_guardian_generator.py -q` from the backend
directory after installing development dependencies.

## License

The shared MetricTrace engine is MIT licensed. This original premium skill
material is separately licensed; see `COMMERCIAL_NOTICE.md`.
