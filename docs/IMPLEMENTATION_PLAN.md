# Implementation Plan

Phased, additive transformation of the current linear NL→SQL pipeline into a
specialist-oriented analysis platform. Constraints honored throughout:
existing functionality is preserved at the end of every phase; the app and
test suite stay green; no capability is claimed unless it executes; new
dependencies only when the existing stack cannot do the job.

Baseline: commit `f631409`, 43 tests passing, ~5s suite runtime.

---

## Phase 1 — Baseline (DONE)
- Repo inspected end-to-end; app runs locally (backend :8011 with
  `AUTH_BYPASS=true`, frontend on Vercel + local).
- Full test suite green; offline LLM tier verified end-to-end via pipeline
  smoke test.
- Produced `ARCHITECTURE.md` and `CAPABILITY_MATRIX.md` (this plan completes
  the Phase-1 doc set).

## Phase 2 — Core abstractions (no behavior change)
New modules, existing pipeline refactored onto them without altering outputs:
- `core/registry.py` — `Specialist`, `Skill`, `Tool` dataclasses + registries
  with capability lookup.
- `core/artifacts.py` — `Artifact` (id/type/source/content/dependencies) +
  artifact store (DB table, replacing ad-hoc `query_results` threading).
- `core/planning.py` — `TaskPlan`, `ExecutionResult`, `ValidationResult` models.
- `tools/base.py` — `Tool` protocol: id/description/input schema/permissions/
  `execute()`; register the 5 existing tools as the first entries.
- Acceptance: all 43 existing tests still pass; SSE event contract unchanged.

## Phase 3 — Data intelligence
- `data/ingestion.py` — `DatasetDescriptor` + ingestion for uploaded CSV/TSV/
  Excel/JSON → DuckDB-backed table alongside existing DB connections; upload
  validation, size limits, type sniffing.
- `data/profiler.py` — staged profiling (fast → deep) persisted per dataset;
  missingness, cardinality, distributions, correlations, candidate keys,
  semantic-type hints (temporal/geo/text/identifier/measure).
- `data/semantic.py` — semantic metadata layer (business meaning, aliases,
  units, dimension/measure roles) consumed by SQL + chart generation.
- Acceptance: upload a messy CSV → profile returned; profile cached/reused.
