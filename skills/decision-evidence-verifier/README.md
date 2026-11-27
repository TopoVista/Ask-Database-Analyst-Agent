# MetricTrace — Decision Evidence Verifier

Commercial skill material for deterministic replay-report verification and
authorized local re-execution. It distinguishes structural validity, digest
integrity, arithmetic reconciliation, and exact result reproduction. It does
not claim author authentication, signature verification, or source custody.

## Install

Install MetricTrace Lite in a Python 3.11 environment:

```bash
pip install metrictrace-lite
```

Copy this directory into a host that supports `SKILL.md`. Supply a complete
report and, for reproduction, only user-authorized CSV/Parquet files and SQL.
No AI key is required. Windows Python 3.11 is the validated environment;
Linux and macOS have not been validated.

## Test

From the repository's `backend` directory with development dependencies:

```bash
python -m pytest app/tests/test_metrictrace_lite.py -q
python C:/Users/KIIT0001/.codex/skills/.system/skill-creator/scripts/quick_validate.py ../skills/decision-evidence-verifier
```

Before marketplace release, test from a freshly extracted archive. This skill
uses the versioned shared `metrictrace` CLI rather than including a separate
replay implementation.

## License

The shared MetricTrace engine is MIT licensed. This original premium skill
material is separately licensed; see `COMMERCIAL_NOTICE.md`.
