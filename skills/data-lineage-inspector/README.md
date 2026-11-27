# MetricTrace — Schema & Lineage Inspector

Commercial skill material for conservative static SQL dependency inspection.
It reports authorized source tables, CTE context, output expressions and
transformations, plus static source/output changes between two definitions.
It does not pretend to prove runtime, row-level, or dynamic-SQL lineage.

## Install

Install MetricTrace Lite in a Python 3.11 environment:

```bash
pip install metrictrace-lite
```

Copy this directory into a host that supports `SKILL.md`. Supply SQL text and
an explicit table allow-list. No API key is required. Windows Python 3.11 is
the validated environment; Linux and macOS are not claimed as tested.

## Test

From the repository's `backend` directory with development dependencies:

```bash
python -m pytest app/tests/test_lineage.py app/tests/test_mcp_protocol.py -q
python C:/Users/KIIT0001/.codex/skills/.system/skill-creator/scripts/quick_validate.py ../skills/data-lineage-inspector
```

Before a marketplace release, validate from a freshly extracted release
archive. This skill delegates to the versioned shared `metrictrace` CLI and
does not ship a duplicate SQL-analysis implementation.

## License

The shared MetricTrace engine is MIT licensed. This original premium skill
material is separately licensed; see `COMMERCIAL_NOTICE.md`.
