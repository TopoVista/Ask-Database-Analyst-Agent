# MetricTrace baseline audit

Audit date: 2026-11-27. Repository was on `main` with one pre-existing
untracked directory: `docs/.docx_deps/`; it was not modified.

## Existing, retained foundations

- FastAPI with async SQLAlchemy, Alembic, Clerk authentication and encrypted
  database connection credentials.
- Next.js App Router, Tailwind, TanStack Query and a polished dashboard shell.
- Read-only SQL validation using SQLGlot and deterministic no-key LLM fallbacks.
- Existing dataset ingestion, profiling, history, connection and specialist flows.

## Baseline results

- Backend `pytest -q` initially could not collect: the local Python environment
  was missing `sentry_sdk` despite it being pinned in `requirements.txt`.
- Frontend `npm run build` was started before changes; it entered Next's
  optimized build phase and reported only the stale Browserslist warning before
  the tool time window elapsed.

## Architectural gaps and risks

- Ownership was user-scoped; no workspace membership or role model existed.
- Uploaded datasets were SQLite files under an ephemeral upload directory, not
  immutable historical versions.
- There were no metric definitions, historical executions, replay cells,
  provenance receipts, contracts or durable worker jobs.
- The Render free web service is intentionally insufficient for continuous CDC
  and unbounded historical processing.
- Existing deployed docs overstate several specialist capabilities relative to
  the code. MetricTrace documentation below separates implemented work from
  planned work.

## Post-change verification

- `pytest -q`: 164 passed in 27.36 seconds.
- `pytest -q app/tests/test_metrictrace.py`: 1 passed in 1.24 seconds.
- `alembic upgrade head` against a fresh SQLite database reached migration
  `005_add_metrictrace_foundations`.
- `npm run build`: completed successfully; `/replay` is included in the
  production route manifest. Browserslist emitted only its stale-data warning.
