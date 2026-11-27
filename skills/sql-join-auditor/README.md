# MetricTrace — SQL Join Auditor

Commercial skill material for evidence-backed local SQL join-cardinality
inspection. It detects actual duplicate key groups, nulls, unmatched rows,
joined row counts, supported aggregate context, and possible amplification
signals. It does not guess results for unsupported join syntax.

## Install

Install MetricTrace Lite in a Python 3.11 environment:

```bash
pip install metrictrace-lite
```

Copy this directory into a skill-compatible host. Supply an explicitly
authorized CSV/Parquet manifest and SQL file. No AI API key is required. Only
Windows Python 3.11 is validated; Linux and macOS are not claimed as tested.

## Test

From the repository's `backend` directory with development dependencies
installed:

```bash
python -m pytest app/tests/test_join_audit.py -q
python C:/Users/KIIT0001/.codex/skills/.system/skill-creator/scripts/quick_validate.py ../skills/sql-join-auditor
```

The runner must also be tested from an extracted archive before marketplace
release. This skill does not contain a runner implementation; it invokes the
versioned shared `metrictrace` CLI.

## License

The shared MetricTrace engine is MIT licensed. This original premium skill
material is separately licensed; see `COMMERCIAL_NOTICE.md`.
