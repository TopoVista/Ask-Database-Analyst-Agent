# MetricTrace product specification

MetricTrace is a time-travel debugger for business metrics. It reproduces a
metric from exact historical inputs, distinguishes data movement from
definition movement, and exposes the evidence used for that conclusion.

## Implemented scope

- Personal workspace creation and workspace-scoped metadata authorization.
- Immutable local development snapshots written as Parquet plus a hashed,
  canonical manifest.
- Versioned SQL metric definitions guarded by the existing SQLGlot read-only
  validator.
- DuckDB scalar execution against the selected Parquet snapshot.
- Four-way replay: old/new data crossed with old/new definitions.
- Symmetric data, definition and interaction attribution that verifies its own
  reconciliation.
- A fully deterministic canonical fixture where original Monday revenue is
  ₹24 lakh and corrected data produces ₹18 lakh with the same definition.

## Explicitly not implemented

The current slice does not provide PostgreSQL consistent snapshot capture,
S3/MinIO persistence, CDC, bitemporal mutable facts, a durable background
worker, contracts, incidents, receipts, lineage or AI investigation tools.
The local storage adapter is for development only and must be replaced or
mounted on durable storage in a hosted deployment.
