# Architecture — Ask-Database-Analyst-Agent

> Phase-1 reconnaissance document. Describes the system **as it exists today**
> (commit `f631409`). Nothing here is aspirational; unimplemented capabilities
> are listed in [`CAPABILITY_MATRIX.md`](CAPABILITY_MATRIX.md) and the roadmap
> for closing gaps lives in [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md).

## 1. System overview

```text
Frontend (Next.js 15, App Router, Clerk auth, Tailwind, recharts)
   │  SSE streaming + REST via Next.js route handler proxy
   ▼
Backend API (FastAPI, /api/v1)
   │  routers: queries, simulate, connections, sessions, schema, auth
   ▼
Agent orchestration (app/agents)          LLM layer (app/services/llm_service.py)
   │  AgentPipeline — fixed linear          OpenAI → Ollama → deterministic
   │  workflow (single shape)               offline fallback; 3-tier, model-agnostic
   ▼
Tools (app/tools)
   │  schema_inspector, sql_executor, sql_validator,
   │  anomaly_detector, chart_recommender
   ▼
Data access (SQLAlchemy async engines)
   ▼
## 2. Layer-by-layer detail

### 2.1 Frontend (`frontend/`)
- Next.js App Router: landing `/`, auth group `(auth)` (Clerk sign-in/up),
  dashboard group `(dashboard)` → `/dashboard`, `/connections`, `/history`.
- **Streaming:** `src/hooks/useStreamingQuery.ts` consumes Server-Sent Events
  from `POST /api/v1/queries/run`. Events: `step`, `intent`, `plan`,
  `query_result`, `analysis`, `hypotheses`, `insight_delta`, `done`, `error`.
- **API proxy:** `src/app/api/[...path]/route.ts` forwards to the backend using
  `BACKEND_API_URL` / `NEXT_PUBLIC_BACKEND_API_URL`, falling back to
  `DEFAULT_PRODUCTION_BACKEND_URL` on Vercel, else `http://127.0.0.1:8011`.
- **Charts:** `src/components/results/ChartRenderer.tsx` renders recharts from
  a backend-provided `chart_spec` (type/x/y) when present, with a deterministic
  frontend fallback otherwise. `ResultsPanel.tsx` composes tables, charts,
  analysis, hypotheses and the streamed insight narrative.
- **Auth:** Clerk middleware (`src/middleware.ts`) guards dashboard routes.
  All Clerk env vars are required; there is no dev bypass on the frontend.

### 2.3 Agent orchestration (`backend/app/agents/`)
- `pipeline.py` — **the only orchestrator**. Fixed linear workflow:
  `SchemaInspector → IntentAgent → PlannerAgent → [per plan task:
  SQLGeneratorAgent → (retry ×3 via fix_sql) → SQLExecutor →
  ChartRecommenderAgent] → ResultAnalyzerAgent (+ AnomalyDetector) →
  HypothesisAgent → InsightAgent (streamed narrative)`.
  Persists `QueryHistory`; no intent-based branching. Simulation runs through
  `simulation_agent.py` via the separate `/simulate` route, not this pipeline.
- `intent_agent.py` — classifies into 6 intents (diagnostic, exploratory,
  comparative, anomaly_detection, simulation, predictive) with entities.
- `planner_agent.py` — produces a small task list (SELECT-style tasks).
- `sql_generator_agent.py` — schema-grounded NL→SQL; `fix_sql()` returns
  `None` (not a placeholder) when repair fails; PII redaction on samples.
- `result_analyzer_agent.py` — statistical summary of rows + anomaly scores.
- `hypothesis_agent.py` — generates diagnostic hypotheses + validation SQL.
- `insight_agent.py` — streams the final NL narrative.
- `chart_recommender_agent.py` — LLM-first chart-type choice with a
  deterministic rule-based fallback (`tools/chart_recommender.py`).
- `base.py` — minimal `BaseAgent` (LLM handle only; no shared contract).

### 2.4 Tools (`backend/app/tools/`)

### 2.6 LLM layer (`backend/app/services/llm_service.py`)
- Tiered: **OpenAI → Ollama (self-hosted, `OLLAMA_BASE_URL`) → deterministic
  offline fallback** (`_local_*` regex/template generators for intent, plan,
  SQL, analysis, hypotheses, insight, chart spec). The offline tier makes every
  workflow runnable with zero API keys — the basis of the test suite.
- Response caching (`memory/query_cache.py`), PII redaction gate
  (`services/redaction.py`, `REDACT_PII_IN_PROMPTS`).

### 2.7 Memory (`backend/app/memory/`)
- `session_memory.py` — Redis-or-in-process conversation history.
- `vector_memory.py` — cosine-similarity recall over prior Q&A embeddings
  (Python-side scan, per-user; fine at small scale, not ANN-indexed).
- `embedding_service.py` — OpenAI `text-embedding-3-small`, with a
  deterministic lexical n-gram hashing fallback (no random vectors).

### 2.8 Security (`backend/app/middleware/`, `services/encryption_service.py`)
Clerk JWT verification (bypass flag for dev), per-user ownership checks on
connections/sessions, Fernet encryption of stored DB credentials, rate
limiting, request logging, SQL validation (read-only enforcement), PII
redaction before LLM prompts.

### 2.9 Deployment
- Backend: Render (`backend` build/start via pip + uvicorn).
- Frontend: Vercel (auto-deploys `main`; deployment verified working).
- DB for app state: PostgreSQL (`DATABASE_URL`), SQLite default for local dev.

## 3. What is deliberately NOT present (yet)
File upload/ingestion of CSV/Excel/PDF/etc. · Python/code execution engine ·
Vector store abstraction or real RAG over documents · Specialist/skill/tool
registries · Intent-based routing to alternative pipelines · Dashboard spec /
renderer · Critic/repair loop beyond SQL retry · MCP integration · Semantic
column metadata · Provenance beyond `QueryHistory` rows.

These gaps are tracked honestly in [`CAPABILITY_MATRIX.md`](CAPABILITY_MATRIX.md).

| Tool | Notes |
|---|---|
| `schema_inspector.py` | Tables, columns, FKs, row counts via async SQLAlchemy |
| `sql_executor.py` | Executes read-only SQL, caps rows/time |
| `sql_validator.py` | sqlglot parse; blocks DML/DDL; requires SELECT/WITH |
| `anomaly_detector.py` | z-score + IQR outlier detection on result columns |
| `chart_recommender.py` | Rules: line/bar/scatter/metric/table + `coerce_chart_spec()` |

Tools are plain classes invoked directly by the pipeline — there is **no tool
registry, no permission model, no capability discovery**.

### 2.5 Data & persistence (`backend/app/models/`)
SQLAlchemy models: `User`, `Connection` (encrypted credentials), `Session`,
`QueryHistory` (question, plan, SQL, analysis, insight — de-facto provenance
and audit trail), `QueryEmbedding` (vector recall), `SchemaCache`.


### 2.2 Backend API (`backend/app/api/v1/`)
| Router | Purpose |
|---|---|
| `queries.py` | `POST /run` (SSE pipeline stream), history, follow-ups |
| `simulate.py` | `POST /simulate/what-if` — separate pipeline for simulations |
| `connections.py` | CRUD for user DB connections (credentials Fernet-encrypted) |
| `sessions.py` | Conversation sessions |
| `schema.py` | Schema inspection endpoint |
| `auth.py` | Clerk token verification; `AUTH_BYPASS=true` dev mode |

PostgreSQL / BigQuery / SQLite user databases (read-only by validation)
```
