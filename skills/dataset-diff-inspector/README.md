# MetricTrace — Dataset Diff Inspector

Commercial skill material for deterministic, key-aware local CSV/Parquet
comparison. It identifies schema changes, validates stable keys, reports
inserted/deleted/modified rows when keys are valid, and uses honest multiset
semantics without keys.

## Install

Install MetricTrace Lite in a Python 3.11 environment:

```bash
pip install metrictrace-lite
```

Copy this directory into an agent host that supports `SKILL.md`, then provide
explicitly authorized input files. No AI API key is required. The validated
environment is Windows Python 3.11; Linux and macOS have not been validated.

## Test

From the repository's `backend` directory with development dependencies:

```bash
python -m pytest app/tests/test_dataset_diff.py -q
python C:/Users/KIIT0001/.codex/skills/.system/skill-creator/scripts/quick_validate.py ../skills/dataset-diff-inspector
```

Before a marketplace release, validate from a freshly extracted release
archive. This skill delegates to the versioned shared `metrictrace` CLI rather
than shipping a duplicate algorithm.

## License

The shared MetricTrace engine is MIT licensed. This original premium skill
material is separately licensed; see `COMMERCIAL_NOTICE.md`.
