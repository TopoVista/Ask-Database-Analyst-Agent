# Historical Metric Debugger 0.1.1rc1 candidate

This is a local, unsubmitted compliance candidate. It preserves the frozen
0.1.0 archive and its checksum unchanged. The only product-material change is
that unsupported multi-table and report-verification workflows are reported as
unsupported rather than directing a buyer to a separate product or workflow.

## Artifact

- `release/historical-metric-debugger-0.1.1rc1.zip`
- SHA-256: `5cad70bfe93018a35d3a2e782ccde7c1fcd5eaf7f535fd76ee07fe1c28e3dc79`

## Local validation

- Standard SKILL.md validation: passed.
- Deterministic archive inspection: passed; six expected UTF-8 source/text
  files, no binary/environment files, secret patterns, external links, or
  off-platform-routing text.
- Extracted standalone runner: passed on Windows/Python 3.11 against the
  synthetic CSV/SQL fixture. It produced A/B/C/D = 2,400,000 / 2,100,000 /
  2,220,000 / 1,800,000 and reconciled a -600,000 total change.
- Fresh extracted-environment installation: passed. A temporary Python 3.11
  virtual environment installed only the declared `duckdb==1.1.3` and
  `sqlglot==25.31.4` dependencies, then ran the extracted script successfully.

## Status and limits

This candidate is not a replacement for the user-specified 0.1.0 listing
version until the copyright holder approves the version and listing change.
It has not been uploaded, submitted, reviewed, approved, published, priced,
or sold. Only Windows/Python 3.11 has been validated. Its dependencies remain
user-authorized `duckdb==1.1.3` and `sqlglot==25.31.4`; no dependencies are
bundled.
