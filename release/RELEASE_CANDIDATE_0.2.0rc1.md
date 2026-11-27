# MetricTrace Lite 0.2.0rc1

This is a local-only release candidate. It has not been uploaded, submitted,
approved, published, or pushed.

## New deterministic capabilities

- Dataset comparison for CSV/Parquet: stable-key validation, schema changes,
  bounded evidence, and keyless multiset mode.
- Declarative local metric contracts with fail-closed mandatory outcomes.
- Baseline/candidate SQL regression checks with explicit numeric gates.
- Data-backed supported SQL join-cardinality audit.

## Interfaces

The same engine is available from the Python package, JSON-first CLI and local
stdio MCP server. Local mode requires no AI API key. The validated environment
is Windows with Python 3.11; Linux and macOS are not claimed as validated.

## Validation

- Wheel clean-install and packaged `metrictrace demo` execution: passed from
  an isolated temporary Windows Python 3.11 virtual environment.
- Backend suite before packaging: `192 passed, 2 skipped in 50.73s`.
- The two skips require Windows symlink permission and an explicitly supplied
  PostgreSQL integration URL, respectively.
- 0.1.0 artifacts remain unchanged; see `SHA256SUMS.txt`.

## Artifacts

- `backend/dist/0.2.0rc1/metrictrace_lite-0.2.0rc1-py3-none-any.whl`
- `backend/dist/0.2.0rc1/metrictrace_lite-0.2.0rc1.tar.gz`
- `release/SHA256SUMS-0.2.0rc1.txt`

This candidate includes no credentials, telemetry, external service dependency,
or bundled runtime environment.
