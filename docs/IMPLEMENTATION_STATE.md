# MetricTrace implementation state

Last updated: 2026-11-28

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
| Four-way replay queue foundation and Replay Lab | PARTIAL | Durable jobs, lease fencing, independent heartbeats and queued replay-cell execution exist. Replay Lab now discovers the authenticated workspace without fixture creation; it selects authorized source/version/metric/definition pairs, enforces same-source and same-metric compatibility in both client and service layers, submits asynchronously, stores replay IDs in the URL, polls authoritative cell-level state through refreshes, represents queued/running/retryable/failed/cancelled states, supports authorized cancellation, and withholds attribution until all four cells complete. This was committed and pushed as `b9e951d`. PostgreSQL multi-worker experiments and browser E2E validation have not run. |
| PostgreSQL source snapshot capture | PARTIAL | Authenticated source registration queues `SNAPSHOT_CAPTURE` work. Its worker path uses one read-only `REPEATABLE READ` PostgreSQL transaction, bounded cursors, typed Parquet batches and immutable verified objects without retaining the metadata transaction through source I/O. The Data Sources workspace now lists tenant-scoped source/version history, performs bounded catalog discovery on an authorized PostgreSQL connection, classifies each table with the same compatibility rules as capture, registers selected tables, explicitly queues captures, and polls durable capture status. Owner-configured bounded intervals enqueue idempotent capture jobs through a separate scheduler process. The real MVCC test and a live scheduler/worker run remain environment-gated because no authorized PostgreSQL service or Docker engine is available. |
| Immutable object storage | PARTIAL | Local and S3-compatible stores now receive verified, unique attempt-scoped Parquet objects and a manifest published only after verification. An explicit, retention-bounded maintenance primitive can remove unreferenced stale attempt prefixes; it has no public API or scheduler, so state changes remain separately authorized. Live MinIO verification is still unimplemented. |
| Docker infrastructure validation | BLOCKED | Docker CLI 28.1.1 is installed with `desktop-linux`, but its Linux engine pipe is absent: `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.` `docker compose config --quiet` succeeded; no containers were started or validated. A local PostgreSQL 15 Windows service is listening on port 5432, but its default `postgres` account rejected the available passwordless connection; no credentials were requested or guessed. |
| Dataset diff | PARTIAL | Shared Lite engine compares CSV/Parquet using DuckDB, with stable-key validation, schema changes, bounded evidence, keyless multiset mode, CLI JSON/Markdown and an MCP tool. The platform now adapts tenant-owned immutable version IDs—not user paths or storage keys—to that same engine, materializes one authorized Parquet object per version into bounded private temporary files, requires explicit table choice for multi-table captures, and exposes the result through the Dataset Diff workspace. The `dataset-diff-inspector` skill documents the shared CLI and passes SKILL validation. Historical multi-table capture comparison and marketplace ZIP validation remain untested against live PostgreSQL/MinIO infrastructure. |
| Metric contracts | PARTIAL | Shared Lite engine evaluates declarative JSON contracts with PASS/FAIL/ERROR/NOT_EVALUATED states. It supports required columns, types, non-null/min/max/non-negative, key uniqueness, absolute/percentage change, referential integrity, freshness, bounded read-only SQL assertions and cross-metric reconciliation; CLI/MCP are wired. The platform now has tenant-scoped immutable contract-definition versions, explicit historical evaluation actions, durable evidence records bound to exact dataset content hashes and definition hashes, and a Contracts workspace to save/evaluate/view real outcomes. It delegates execution to the shared engine and accepts no user file paths. Shadow execution, transactional promotions, stale-approval fencing, and a release ZIP remain unimplemented. |
| SQL regression | PARTIAL | Shared Lite engine executes baseline and candidate read-only SQL against identical authorized local datasets, records values/duration/differences/fingerprints, and enforces explicit absolute or percentage gates. CLI and MCP are wired with stable CI failure exits. The platform exposes the same engine through a tenant-scoped immutable-version API with optional multi-table selection and typed parameters; client paths cannot be supplied. The SQL Regression workspace selects evidence, evaluates baseline/candidate SQL, and renders actual gate outcomes, timings, normalized SQL, and evidence fingerprints. Immutable named regression-policy versions and shadow executions bind the policy hash, exact baseline/candidate definition versions, immutable dataset content hash, gate report, and optional required contract report; a gate cannot pass when its required contract fails. A one-time PASS shadow record can atomically activate only its exact candidate, supersede the prior active definition, and produce a durable promotion receipt while rejecting consumed, FAIL, non-candidate, or stale policy/contract/dataset bindings. The Shadow Runs workspace creates policies, selects authenticated immutable inputs, runs gates, displays retained evidence, and makes the explicit one-time promotion action. A release ZIP remains unimplemented. |
| Join audit | PARTIAL | Shared Lite engine profiles supported direct equality joins against actual CSV/Parquet data: key cardinality/duplicates/nulls, unmatched rows, joined rows, aggregate context and potential amplification. CLI/MCP are wired. Unsupported joins return uncertainty. The platform exposes a tenant-scoped immutable-version API that materializes only manifest-declared tables under deterministic SQL names before delegating to the shared engine. The SQL Join Auditor workspace selects historical inputs and displays observed join/unmatched/duplicate evidence, aggregate-amplification warnings, and explicit uncertainty. The `sql-join-auditor` skill documents the shared CLI and passes SKILL validation. A tested marketplace ZIP remains unimplemented. |
| Static SQL lineage | PARTIAL | Shared Lite engine now inspects authorized read-only SQL without data access, reporting source tables, CTE contexts, output expressions, transformation functions, explicit uncertainty and fingerprints. A comparison command reports static source/output surface changes. Tenant-scoped Platform API, CLI/MCP, and the `data-lineage-inspector` skill use that same implementation. This is not persisted platform lineage, database-catalog lineage, runtime-plan lineage, row-level lineage, or dynamic SQL support. |
| Decision evidence | PARTIAL | Local reports retain canonical integrity digests and four-cell reconciliation. Each local report now includes a versioned decision receipt with exact file and SQL evidence, engine/compiler versions, explicit unavailable platform identifiers and limitations. The shared verifier also supports authorized deterministic re-execution after it checks exact data-file identities, SQL hashes, and parameters, returning explicit `REPRODUCED`, input-mismatch, result-mismatch, missing-evidence, or execution-failure outcomes. CLI and the `decision-evidence-verifier` skill are wired. Platform receipt persistence, dataset-version identifiers, contract outcomes, signing, retention state, and remote re-execution remain unimplemented. |

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
- Focused local-report/receipt tests: `10 passed, 1 skipped`; scoped Ruff for
  the receipt changes: passed. The skip remains the Windows symlink-permission
  case.

Validation after the Replay Lab integration (pending its cohesive commit):

- Replay API and worker tests: `6 passed in 7.16s`
  (`app/tests/test_metrictrace.py`, `app/tests/test_async_replay.py`). These
  include authenticated workspace bootstrap and cancellation fencing coverage.
- Scoped Ruff over the changed MetricTrace API, service, queue, and tests:
  passed.
- Frontend TypeScript: `npx tsc --noEmit` passed.
- Frontend lint: `npm run lint` passed with no warnings or errors.
- Frontend production build: `npm run build` produced `.next/BUILD_ID`.
  The command runner returned while Next retained child processes, so this is
  recorded as artifact confirmation rather than a captured clean exit line.

Validation after PostgreSQL catalog discovery and Data Sources UI (pending its cohesive commit):

- Capture and MetricTrace API tests: `8 passed, 1 skipped in 6.25s`
  (`app/tests/test_postgres_capture.py`, `app/tests/test_metrictrace.py`). The
  skipped MVCC test requires `METRICTRACE_TEST_POSTGRES_URL`.
- Scoped Ruff and `git diff --check`: passed.
- Frontend TypeScript and lint: passed with no warnings or errors. `npm run
  build` was started and produced the optimized-build stage; its child process
  outlived the command output window, so a clean build exit is not claimed
  until its final artifact is observed.

Validation after Dataset Diff platform integration (pending its cohesive commit):

- Dataset Diff, capture, and MetricTrace API tests: `14 passed, 1 skipped in
  7.58s` (`app/tests/test_dataset_diff.py`, `app/tests/test_postgres_capture.py`,
  `app/tests/test_metrictrace.py`). The skipped MVCC test requires
  `METRICTRACE_TEST_POSTGRES_URL`.
- Scoped Ruff, frontend TypeScript, and frontend lint: passed with no warnings
  or errors.

Validation after SQL Regression platform API integration (pending its cohesive
commit):

- MetricTrace SQL regression and shared regression tests: `10 passed in
  13.52s` (`app/tests/test_metrictrace.py`, `app/tests/test_regression.py`).
- Scoped Ruff and `git diff --check`: passed.
- The SQL Regression workspace passes frontend TypeScript and lint without
  warnings. Its production build compiled and completed, with a fresh
  `.next/BUILD_ID` observed; the command runner does not retain the child exit
  code for a stronger assertion.

Validation after Join Auditor platform API integration (pending its cohesive
commit):

- MetricTrace Join Auditor and shared engine tests: `11 passed in 13.30s`
  (`app/tests/test_metrictrace.py`, `app/tests/test_join_audit.py`).
- Scoped Ruff: passed.
- The SQL Join Auditor workspace passes frontend TypeScript and lint.

Validation after Metric Contract Guardian platform integration:

- Contract API and shared evaluator tests: `13 passed in 14.51s`
  (`app/tests/test_metrictrace.py`, `app/tests/test_contracts.py`). This covers
  immutable definition version increments, persisted evidence, PASS outcomes,
  listing the last evaluation, and cross-workspace denial.
- Scoped Ruff over the changed models, service, API, schema, migration, and
  tests: passed.
- A fresh SQLite Alembic upgrade ran from revision `001` through
  `009_add_metric_contracts`: passed.
- Frontend TypeScript and lint: passed with no warnings or errors.
- Frontend production build compiled successfully and entered Next.js type
  validation; the runner returned before its child process yielded a final
  exit line, so a full clean build exit is not claimed.

Validation after persisted shadow execution gates:

- Shadow, contract, and shared SQL-regression tests: `16 passed in 20.29s`
  (`app/tests/test_metrictrace.py`, `app/tests/test_regression.py`,
  `app/tests/test_contracts.py`). This includes a persisted FAIL gate using
  the canonical `300000` absolute difference against a `250000` policy.
- Scoped Ruff over the changed core, platform service/API/models/schemas,
  migration, and tests: passed.

Validation after transactional metric promotion:

- Shadow, promotion, contract, and shared SQL-regression tests: `17 passed in
  19.08s` (`app/tests/test_metrictrace.py`, `app/tests/test_regression.py`,
  `app/tests/test_contracts.py`). This covers FAIL-evidence rejection and
  single-use PASS-evidence promotion.
- A fresh SQLite Alembic upgrade ran from revision `001` through
  `011_add_metric_promotions`: passed.
- Scoped Ruff over changed platform models/service/API/schemas, migration,
  and tests: passed.

Validation after Shadow Runs workspace:

- Frontend TypeScript and lint: passed with no warnings or errors.
- Frontend production build compiled, type-checked, collected page data, and
  produced a fresh `.next/BUILD_ID`; the command runner did not preserve a
  final clean child-process exit line.

## Delivery note

The current branch is `codex/metrictrace-foundations`. Commit `387442d` is
pushed. The subsequent validated `cc6c606` checkpoint is locally committed,
but Git Credential Manager stalled before it could authenticate a push; the
promotion checkpoint is also local pending that external authentication path.
No work has been deployed, published, submitted, or monetized.

## Exact next executable task

Run the environment-gated PostgreSQL MVCC test against a disposable instance
(`METRICTRACE_TEST_POSTGRES_URL`) if authorized credentials or Docker become
available. In parallel, implement persisted decision receipts, then perform
multi-worker failure experiments (claim contention, lease expiry, stale
publication rejection and worker termination).
