# MetricTrace migration plan

## Completed vertical slice

1. Add workspace-scoped metadata and migrations without altering legacy users,
   connections, sessions, query history or uploaded datasets.
2. Add a local immutable Parquet storage adapter. A version is published only
   after its Parquet object, schema and hash manifest are complete.
3. Add immutable metric definitions and DuckDB execution of a read-only scalar
   query against an exact Parquet version.
4. Add four-way replay cells and a symmetric attribution calculation; failed
   cells remain failed and do not receive numeric values.
5. Add a no-AI fixture and the Replay Lab frontend.

## Ordered next work

1. Capture user-imported datasets and configured PostgreSQL sources into the
   version store, including proper repeatable-read boundaries.
2. Move replay submission to a PostgreSQL-leased worker with cancellation,
   retries, fencing tokens and recovery tests.
3. Implement metric contracts, incident workspaces and portable decision
   receipts from completed executions.
4. Add S3/MinIO storage, snapshot retention, schema versions and lineage.
5. Add CDC only after exported-snapshot/LSN bootstrap and slot operations are
   explicitly designed and authorized.

Legacy chat/query history is retained as legacy analysis and is not treated as
reproducible MetricTrace evidence.
