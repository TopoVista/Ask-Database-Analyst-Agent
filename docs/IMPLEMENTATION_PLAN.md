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

## Phase 4 — Specialist orchestration layer
- **Objective:** Wire the `core/registry.py` Specialist/Tool/Skill registries to
  the existing agents and tools; add intent-based routing without breaking the
  SSE event contract.
- Create `tools/base.py` — a `Tool` Protocol (`id`/`name`/`description`/
  `input_schema`/`permissions`/`execute()`); register the 5 existing tools
  (schema_inspector, sql_executor, sql_validator, anomaly_detector,
  chart_recommender) as `ToolSpec` entries.
- Create `app/specialists/` package — register the 6 existing agents as
  `Specialist` entries with declared capabilities, tools, and `available=True`
  only where a real workflow backs every capability.
- Intent-based routing in `AgentPipeline`:
  - `diagnostic` → SQL + analysis + hypothesis generation + validation SQL
    (existing behaviour, now via SpecialistRegistry lookup)
  - `exploratory` → SQL + EDA summary + chart recommendation
  - `anomaly_detection` → SQL + anomaly scan on result columns
  - `comparative` → SQL + comparison analysis
  - `predictive` → SQL + trend analysis (forecast stub emits a clear plan)
  - `simulation` → redirect to `SimulationAgent` (separate flow)
- Integrate `ArtifactStore` into the pipeline: persist SQL results, chart specs,
  analysis, and insights as typed Artifacts (table/chart/analysis/insight)
  keyed by session.
- Acceptance tests: existing 60 tests green; new tests for specialist lookup,
    intent routing dispatch, and artifact creation/retrieval.

## Phase 5 — Data-intelligence specialists (EDA + statistics)
- EDA Agent: richer profiling at query time (distribution stats, top-N
  breakdowns, correlation hints) using the deep-profile data from the dataset
  descriptor.
- Statistics Agent: significance testing, confidence intervals, trend
  direction/magnitude — replacing the current rule-based `_local_analysis`
  with scipy-backed computation (scipy already installed).
- Anomaly Detection Agent: extend the z-score/IQR detector to support
  time-windowed anomaly detection (rolling z-score) on uploaded datasets.
- Visualization Agent: LLM-first chart-type selection with the deterministic
  rule-based fallback already in place; add multi-chart dashboard-spec
  generation (a list of chart specs for a single result set).
- Acceptance: upload → EDA summary with statistics; anomaly detection on a
  result set returns actionable outliers; tests for statistical helpers.

## Phase 6 — Document intelligence & RAG (DONE)
- `rag/parser.py` — `parse_document()` for TXT/MD/HTML/PDF → extracted text + metadata.
- `rag/chunker.py` — sentence-based chunking with overlap, character offsets.
- `rag/vector_store.py` — `VectorStore` abstraction; `InMemoryVectorStore` (cosine
  similarity) + `ChromaVectorStore` (when `CHROMA_HOST` set); factory `get_default_store()`.
- `rag/retriever.py` — `RAGRetriever`: ingest → chunk → embed → store with user_id;
  retrieval scoped by user_id + optional source filter.
- Per-user access control enforced at ingest (user_id tag) and retrieval (filter).
- Acceptance: 31 new tests green (parser, chunker, vector store, retriever); full suite 91/91.

## Phase 7 — MCP (Model Context Protocol) integration (DONE)
- `mcp/client.py` — `MCPClient` + `MCPTransport` protocol with `HTTPMCPTransport`
  and `StdioMCPTransport` implementations; tool discovery and invocation.
- `mcp/registry.py` — `MCPRegistry` for managing server lifecycle: register,
  connect_all, list_servers, call_tool, unregister. Singleton `get_mcp_registry()`.
- `MCPServerConfig` dataclass for server configuration (HTTP or stdio).
- 17 new tests green (client tool discovery, call forwarding, error handling,
  registry operations).

## Phase 8 — Automated dashboard generation (DONE)
- `dashboard/specs.py` — `DashboardPanel`, `DashboardSpec`, `PanelLayout` dataclasses
  with serialization; 12-column grid layout; auto-positioning of panels.
- `dashboard/assembler.py` — `DashboardAssembler`: creates panels from query results
  using chart recommender; generates per-panel narratives (metric/line/bar/scatter/
  pie/table); auto-layouts in 2-column grid; overall dashboard summary.
- 21 new tests green (narrative generation, panel creation, assembly, serialization).

## Phase 9 — Expanded specialist library
- NLP/Text Specialist: text columns → tokenization, sentiment, entity
  extraction, summarization using HuggingFace Transformers or spaCy.
- Time-Series/Forecasting Specialist: ARIMA-style forecasting on time-series
  datasets using statsmodels or scikit-learn regression fallback.
- Causal Analysis Specialist: DAG-based causal inference using DoWhy/EconML
  (if installable; otherwise rule-based confounder detection).
- ML Specialist: train/evaluate models on uploaded datasets (scikit-learn),
  with model artifacts persisted in the ArtifactStore.
- Anomaly/Fraud Specialist: extend Phase-5 anomaly detection with isolation
  forest (scikit-learn already installed).
- Acceptance: each specialist has a unit-tested capability; the planner can
  route to them based on intent + schema heuristics.

## Phase 10 — Evaluation, security hardening, optimization
- Evaluation harness: Spider-style NL→SQL accuracy on embedded SQLite datasets;
  EDA correctness checks; dashboard narrative quality rubric.
- Security hardening: enforce read-only SQL; add audit logging of all SQL
  execution and artifact creation; implement document-level access control in
  the vector store (Phase 6).
- Performance optimization: warm-LLM caching, SQLite connection pooling,
  query-result caching keyed on schema+question hash.
- Cost/latency benchmarks: measure offline vs. OpenAI vs. Ollama tiers for
  latency and token cost; document tradeoffs.
- Acceptance: benchmark script producing a report; security scan of all tool
  executors; existing tests green.
