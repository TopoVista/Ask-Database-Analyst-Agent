# Capability Matrix

Status legend: **✅ implemented and tested** · **🟡 partial** (works, with
noted limits) · **❌ absent** (do not assume it exists). Current state:
Phases 1–5 complete, 60 backend tests passing.

## A. Platform capabilities

| Capability | Status | Detail |
|---|---|---|
| NL → SQL over user databases | ✅ | Schema-grounded, PostgreSQL/BigQuery/SQLite; ×3 self-repair; explicit failure instead of placeholder |
| Read-only SQL enforcement | ✅ | `sql_validator` blocks DML/DDL, requires SELECT/WITH, sqlglot-parsed |
| Result statistics + anomaly detection | ✅ | `ResultAnalyzerAgent` + z-score/IQR `AnomalyDetector` |
| Hypothesis generation + validation SQL | ✅ | Diagnostic hypotheses with follow-up queries |
| Streamed narrative insight | ✅ | `InsightAgent` via SSE |
| AI chart selection | ✅ | `chart_spec` per result; rules fallback; frontend renderer |
| What-if simulation | ✅ | Separate `/simulate/what-if` pipeline |
| Multi-LLM tiers (OpenAI/Ollama/offline) | ✅ | Deterministic offline tier keeps app fully runnable keyless |
| Auth (Clerk) + rate limiting + encrypted credentials | ✅ | Dev bypass flag for local runs |
| PII redaction before LLM prompts | ✅ | `REDACT_PII_IN_PROMPTS`-gated |
| Specialist / skill / tool registries | ✅ | `core/registry.py` — `ToolRegistry`, `SkillRegistry`, `SpecialistRegistry` with capability lookup |
| Intent-based routing | ✅ | `specialists/__init__.py` — 6 intents route to specialist combinations |
| Artifact store | ✅ | `core/artifacts.py` — typed, session-keyed outputs (table/chart/analysis/insight/dashboard/profile/model/sql_query/code/document) |
| Data ingestion (CSV/Excel/JSON) | ✅ | `data/ingestion.py` — upload → DuckDB-backed table |
| Data profiling (fast + deep) | ✅ | `data/profiler.py`, `data/profiler_deep.py` — missingness, cardinality, distributions, correlations, candidate keys, semantic-type hints |
| Semantic layer | ✅ | `data/semantic.py` — business meaning, aliases, units, dimension/measure roles |
| Conversation memory | 🟡 | Session history + embedding recall of past Q&A; artifact graph exists but not yet surfaced in UI |
| Provenance | 🟡 | `QueryHistory` + `ArtifactStore`; audit trail present but not user-facing |
| File upload ingestion (Parquet) | 🟡 | CSV/Excel/JSON supported; Parquet pending |
| Python/code execution engine | ❌ | None (by design today) |
| RAG over documents / vector store abstraction | ✅ | `rag/` package: parse TXT/MD/HTML/PDF, sentence chunking, embed, store with per-user scoping; `InMemoryVectorStore` + `ChromaVectorStore` backends |
| Dashboard spec / generation / editing | 🟡 | Single-chart rendering; dashboard spec model exists in artifact store but no multi-panel renderer |
| Critic/repair loop beyond SQL retry | 🟡 | SQL self-repair (×3); no statistical/chart-level validation yet |
| MCP integration | ✅ | `mcp/` package: `MCPClient` with HTTP + stdio transports, `MCPRegistry` for server lifecycle, tool discovery and invocation |
| NLP / forecasting / causal / ML / geospatial | ❌ | Specialist entries registered but `available=False` until workflows exist |

## B. Data types the system can work with today

| Type | Status | Via |
|---|---|---|
| Relational databases (Postgres, BigQuery, SQLite) | ✅ | `connections` + `schema_inspector` |
| CSV/Excel/JSON files | ✅ | `data/ingestion.py` → DuckDB |
| PDF/DOCX/HTML/MD documents | 🟡 | Parser + chunker + embedder for TXT/MD/HTML/PDF; retrieval scoped per-user |
| Time-series columns | 🟡 | Can aggregate/filter via SQL; no dedicated forecasting workflow |
| Geospatial columns | 🟡 | Treated as ordinary columns; no geo detection/maps |
| Text-heavy columns | 🟡 | Treated as ordinary columns; no NLP workflows |
| Images/audio/video | ❌ | No multimodal pipeline |

## C. Specialist-role mapping (target roster → current state)

| Role | Current state | Phase (see plan) |
|---|---|---|
| Data Profiler | ✅ | 3 |
| Data Quality Engineer | 🟡 | 3 (profiling detects issues; no auto-fix yet) |
| SQL/Database Analyst | ✅ | 4 |
| Exploratory Data Analyst | ✅ | 4 |
| Statistician | 🟡 | 5 (basic stats; no hypothesis testing) |
| Visualization Expert | 🟡 | 5/8 (chart-type selection; no multi-panel dashboard) |
| Time-Series/Forecasting Expert | ❌ | 9 |
| Experimentation/A-B Expert | ❌ | 9 |
| Causal Analysis Expert | ❌ | 9 |
| Machine Learning Scientist | ❌ | 9 |
| Anomaly/Fraud Expert | 🟡 | 5/9 (z-score/IQR on single results) |
| NLP Expert | ❌ | 9 |
| Geospatial Analyst | ❌ | 9 |
| Document Intelligence Analyst | 🟡 | 6 (parser + chunker + embedder + retriever; no API endpoint yet) |
| Multimodal Analyst | ❌ | 9 (extension layer only) |
| Data Engineer | ✅ | 3 (ingestion layer) |
| Dashboard/BI Expert | ❌ | 8 |
| Research/Fact-Finding Agent | 🟡 | 6/9 (RAG retriever with per-user scoping exists; agent workflow pending) |
| Reporting/Storytelling Agent | 🟡 | 8/10 (InsightAgent narrates one analysis) |

Rule honored throughout the plan: a role with ❌ stays ❌ in the product until
its workflow actually executes — no persona labels without backing capability.
