# MetricTrace implementation state

Last updated: 2026-11-27

This file records observed, reproducible status. It is not a release claim.

## Preservation boundary

The existing MetricTrace Lite `0.1.0` release artifacts and their recorded
checksums are preserved without rebuilding or overwriting them:

- `backend/dist/metrictrace_lite-0.1.0-py3-none-any.whl`
- `backend/dist/metrictrace_lite-0.1.0.tar.gz`
- `release/historical-metric-debugger.zip`
- `release/SHA256SUMS.txt`

The shared platform and computational engine are MIT licensed with
`Copyright © 2026 Souradeep Ghosh`. Separately scoped original premium
materials retain their existing commercial notices. This is based on the
copyright ownership confirmation supplied by Souradeep Ghosh; third-party
licenses and notices remain unchanged.

## Current milestone status

| Area | Status | Evidence / limitation |
| --- | --- | --- |
| Lite local replay, CLI, SDK and MCP | COMPLETE | Existing 0.1.0 artifacts were locally validated before this roadmap continuation. |
| Four-way replay queue foundation | PARTIAL | Durable jobs, lease fencing, independent heartbeats and queued replay-cell execution exist. PostgreSQL multi-worker experiments have not run. |
| PostgreSQL source snapshot capture | PARTIAL | Authenticated source registration now queues `SNAPSHOT_CAPTURE` work. Its worker path uses one read-only `REPEATABLE READ` PostgreSQL transaction, bounded cursors, typed Parquet batches and immutable verified objects without retaining the metadata transaction through source I/O. The real MVCC test is environment-gated because no PostgreSQL server is available. Scheduled capture is not implemented. |
| Immutable object storage | PARTIAL | Local and S3-compatible stores now receive verified, unique attempt-scoped Parquet objects and a manifest published only after verification. Metadata-aware orphan retention/cleanup and live MinIO verification are still unimplemented. |
| Docker infrastructure validation | BLOCKED | Docker CLI 28.1.1 is installed with `desktop-linux`, but its Linux engine pipe is absent: `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.` `docker compose config --quiet` succeeded; no containers were started or validated. A local PostgreSQL 15 Windows service is listening on port 5432, but its default `postgres` account rejected the available passwordless connection; no credentials were requested or guessed. |
| Dataset diff | PARTIAL | Shared Lite engine now compares CSV/Parquet using DuckDB, with stable-key validation, schema changes, bounded evidence, keyless multiset mode, CLI JSON/Markdown and an MCP tool. The `dataset-diff-inspector` skill now documents the shared CLI and passes SKILL validation. Platform API/UI, historical-snapshot input and a tested marketplace ZIP remain unimplemented. |
| Metric contracts | PARTIAL | Shared Lite engine evaluates declarative JSON contracts with PASS/FAIL/ERROR/NOT_EVALUATED states. It supports required columns, types, non-null/min/max/non-negative, key uniqueness, absolute/percentage change, referential integrity, freshness, bounded read-only SQL assertions and cross-metric reconciliation; CLI/MCP are wired. The `metric-contract-guardian` commercial skill now invokes this engine and passes SKILL validation. Platform persistence/UI and a release ZIP remain unimplemented. |
| SQL regression | PARTIAL | Shared Lite engine executes baseline and candidate read-only SQL against identical authorized local datasets, records values/duration/differences/fingerprints, and enforces explicit absolute or percentage gates. CLI and MCP are wired with stable CI failure exits. The `metric-regression-investigator` commercial skill now invokes this engine and passes SKILL validation. Platform shadow runs, promotion gates, persisted contracts and a release ZIP remain unimplemented. |
| Join audit | PARTIAL | Shared Lite engine profiles supported direct equality joins against actual CSV/Parquet data: key cardinality/duplicates/nulls, unmatched rows, joined rows, aggregate context and potential amplification. CLI/MCP are wired. Unsupported joins return uncertainty. The `sql-join-auditor` skill now documents the shared CLI and passes SKILL validation. Platform API/UI and a tested marketplace ZIP remain unimplemented. |
| Static SQL lineage | PARTIAL | Shared Lite engine now inspects authorized read-only SQL without data access, reporting source tables, CTE contexts, output expressions, transformation functions, explicit uncertainty and fingerprints. A comparison command reports static source/output surface changes. Tenant-scoped Platform API, CLI/MCP, and the `data-lineage-inspector` skill use that same implementation. This is not persisted platform lineage, database-catalog lineage, runtime-plan lineage, row-level lineage, or dynamic SQL support. |
| Decision evidence | PARTIAL | Local reports retain canonical integrity digests and four-cell reconciliation. The shared verifier now also supports authorized deterministic re-execution after it checks exact data-file identities, SQL hashes, and parameters, returning explicit `REPRODUCED`, input-mismatch, result-mismatch, missing-evidence, or execution-failure outcomes. CLI and the `decision-evidence-verifier` skill are wired. Platform receipt persistence, dataset-version identifiers, contract outcomes, signing, retention state, and remote re-execution remain unimplemented. |

## Validation baseline

Initial baseline before this capture change:

- Backend tests: `179 passed, 1 skipped in 58.51s` (the skipped test requires Windows symlink permission).
- Frontend production build: passed (`npm run build`, Next.js 14.2.35).
- Repository-wide Ruff: failed with 81 pre-existing unused-import / import-order / unused-local findings outside the Lite scope. This is not represented as a successful lint run.

Validation after the PostgreSQL capture change:

- Backend tests: `192 passed, 2 skipped in 50.73s`. The two skips are the
  existing Windows symlink-permission test and the intentionally
  environment-gated PostgreSQL MVCC integration test.
- Scoped Ruff over the changed capture, storage, service, API, schema, model
  and test modules: passed.
- Fresh SQLite Alembic upgrade through revision `008_add_postgres_capture_sources`: passed.

## Delivery note

The current branch is `codex/metrictrace-foundations`. The Phase 2 and
commercial-release work through commit `a488b25` is pushed to its origin
branch. No work has been deployed, published, submitted, or monetized.

## Exact next executable task

Run the environment-gated PostgreSQL MVCC test against a disposable instance
(`METRICTRACE_TEST_POSTGRES_URL`), then add metadata-aware stale-attempt
cleanup and PostgreSQL multi-worker failure experiments (claim contention,
lease expiry, stale publication rejection and worker termination). 
