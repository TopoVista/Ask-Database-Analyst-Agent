# MetricTrace implementation report

## Outcome

The repository now contains a runnable, deterministic MetricTrace vertical
slice. It is intentionally smaller than the full target architecture: the
implemented core is real historical capture and replay, not a UI mock.

## Architecture changes

- Added workspace/membership, sources, immutable dataset versions, metrics,
  metric definitions, observations, replay jobs and replay cells.
- Added a local Parquet object-store adapter that writes a staging directory,
  hashes objects and manifest, then atomically publishes the version.
- Added SQLGlot-validated DuckDB execution against an exact version's Parquet
  object and durable replay-cell/observation metadata.
- Added a four-way decomposition: data effect, definition effect, interaction
  effect and total change. The service asserts that the effects reconcile.
- Added the Replay Lab route, backed solely by API output.

## Retained components

FastAPI, async SQLAlchemy, Alembic, Clerk auth, encrypted connection storage,
SQL validation, Next.js, Tailwind, TanStack Query and the existing analytical
workflows remain intact.

## Security and correctness

Workspace access is checked before replay IDs are resolved. SQL remains
read-only and must return one non-null scalar. Snapshot metadata is not marked
ready until object and manifest writing succeeds. Failed cells have no result
value and retain their error.

## Verification

| Check | Result |
| --- | --- |
| Full backend test suite | 164 passed |
| Canonical replay integration test | Passed |
| Alembic fresh-db smoke test | Reached `005_add_metrictrace_foundations` |
| Production frontend build | Passed; `/replay` emitted |
| Premium UI static audit | Passed with zero findings |

## Capability matrix

| Capability | Status | Notes |
| --- | --- | --- |
| Workspace-scoped replay authorization | COMPLETE | Personal workspace is provisioned on first MetricTrace action. |
| Immutable local Parquet snapshot | COMPLETE | Local development adapter only. |
| Versioned metric definition | COMPLETE | Immutable rows with normalized SQL hash. |
| Historical DuckDB execution | COMPLETE | Exact selected snapshot, scalar metric SQL. |
| Four-way replay and attribution | COMPLETE | Canonical ₹24L → ₹18L fixture included. |
| Replay Lab | COMPLETE | Uses backend values and exposes failures. |
| PostgreSQL repeatable-read capture | NOT_STARTED | Imports/fixture only today. |
| Durable worker recovery and leases | NOT_STARTED | Replay metadata is durable; execution is synchronous. |
| Contracts, incidents, receipts | NOT_STARTED | Planned after worker foundation. |
| CDC and bitemporal mutable facts | NOT_STARTED | Requires explicit bootstrap/replication design. |
| S3/MinIO production adapter | NOT_STARTED | Local adapter must not be used on ephemeral hosting. |

## Local run

```powershell
cd backend
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

cd ../frontend
npm install
npm run dev
```

Set `HISTORICAL_STORAGE_DIR` to a mounted durable directory for any non-local
environment. No provider key is required for the Replay Lab fixture.
