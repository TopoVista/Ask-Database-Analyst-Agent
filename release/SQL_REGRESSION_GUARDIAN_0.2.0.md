# SQL Regression Guardian 0.2.0 local package

This is a locally validated, single-skill commercial package candidate. It is
not uploaded, submitted, approved, published, priced, or sold.

## Artifact

- `release/sql-regression-guardian-0.2.0.zip`
- SHA-256:
  `38a93acc7de1913adc9363c8b68231e503842bb9eea13499a2d2bb962e84621a`

## Package contract

- The archive contains exactly one standards-compatible `SKILL.md`, its
  commercial instructional material, MIT `LICENSE`, two declared Python
  dependencies, and a standalone Python runner.
- The runner is generated from the shared deterministic MetricTrace source;
  it does not depend on `metrictrace-lite`, a service, an AI key, Docker, or
  network access.
- It supports one explicitly authorized CSV or Parquet source file named
  `source_data` in SQL. It emits stable JSON and returns exit `0` for gate
  pass, `3` for gate failure, `2` for invalid input, and `4` for execution
  failure.
- Only Windows Python 3.11 has been validated. The buyer installs
  `duckdb==1.1.3` and `sqlglot==25.31.4`; no dependencies are bundled.

## Local validation evidence

- ZIP inspection passed: seven expected UTF-8 text/source files, no detected
  credentials, external links, prohibited binaries, environment files, or
  off-platform-routing language.
- An extracted runner executed against the canonical synthetic CSV and
  correctly emitted an absolute-gate failure with exit code `3`.
- Focused regression, generator, and release-validator tests passed on
  Windows Python 3.11 (`5 passed`).

The package is intentionally retained as a local candidate until a manual
Agensi submission decision and current packaging recheck are completed.
