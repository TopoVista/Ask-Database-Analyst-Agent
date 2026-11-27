# MetricTrace Lite

MetricTrace Lite is a local, deterministic historical metric replay package. It runs four SQL cells across two authorized CSV or Parquet dataset versions and attributes the numerical change to data, definition, and their interaction.

## Install from a local artifact

```bash
python -m pip install metrictrace_lite-0.2.0rc1-py3-none-any.whl
metrictrace demo
```

Python 3.11+ is required. Core installation includes DuckDB and SQLGlot only. Install `metrictrace-lite[mcp]` for the optional local MCP server and `metrictrace-lite[remote]` for authenticated Platform API access.

## Local replay

```bash
metrictrace local-replay --old-dataset old.csv --new-dataset new.csv \
  --old-sql-file old.sql --new-sql-file new.sql --output replay.json
metrictrace verify-report --report replay.json
```

Use `metrictrace --help` for manifest, schema inspection, Markdown, parameter, timeout, and resource-limit options. Local mode does not require Docker, a hosted database, an API key, or network access. Uninstall with `python -m pip uninstall metrictrace-lite`.

## Security and limits

Only explicitly declared CSV/Parquet files and logical tables are registered. SQL file readers, URLs, extensions, attachments, and undeclared tables are rejected. Process and DuckDB limits are best-effort protections, not a full operating-system sandbox; use an isolated account for untrusted files or SQL.

Windows execution has been tested in this repository. The package targets Python 3.11+ on Windows and Linux; Linux and macOS need separate release validation before being claimed as tested.
