# Capability Matrix

Status legend: **✅ implemented and tested** · **🟡 partial** (works, with
noted limits) · **❌ absent** (do not assume it exists). Baseline commit
`f631409`, 43 backend tests passing.

## A. Platform capabilities

| Capability | Status | Detail |
|---|---|---|
| NL → SQL over user databases | ✅ | Schema-grounded, PostgreSQL/BigQuery/SQLite; ×3 self-repair; explicit failure instead of placeholder |
| Read-only SQL enforcement | ✅ | `sql_validator` blocks DML/DDL, requires SELECT/WITH, sqlglot-parsed |
| Result statistics + anomaly detection | ✅ | `ResultAnalyzerAgent` + z-score/IQR `AnomalyDetector` |
| Hypothesis generation + validation SQL | ✅ | Diagnostic hypotheses with follow-up queries |
| Streamed narrative insight | ✅ | `InsightAgent` via SSE |
| AI chart selection | ✅ | `chart_spec` per result; rules fallback; frontend renderer |
| What-if simulation | ✅ | Separate `/simulate/what-if` pipeline (not in main router) |
| Multi-LLM tiers (OpenAI/Ollama/offline) | ✅ | Deterministic offline tier keeps app fully runnable keyless |
| Auth (Clerk) + rate limiting + encrypted credentials | ✅ | Dev bypass flag for local runs |
| PII redaction before LLM prompts | ✅ | `REDACT_PII_IN_PROMPTS`-gated |
| Conversation memory | 🟡 | Session history + embedding recall of past Q&A; no structured analysis state, no artifact graph |
| Provenance | 🟡 | `QueryHistory` stores question/plan/SQL/analysis/insight; not user-facing, no code/tool/retrieval capture |
| File upload ingestion (CSV/Excel/Parquet/JSON…) | ❌ | DB connections only |
| Python/code execution engine | ❌ | None (by design today; needed for Phase 5) |
| RAG over documents / vector store abstraction | ❌ | Only prior-Q&A vector recall; no chunking, retrieval filters, or citations |
| Specialist/skill/tool registries | ❌ | Agents are hardcoded classes in a fixed pipeline |
| Intent-based routing to different pipelines | ❌ | Intent is classified but never changes the workflow |
| Dashboard spec / generation / editing | ❌ | Single-chart rendering only |
| Critic/repair loop beyond SQL retry | ❌ | No statistical/chart-level validation |
| Semantic layer (business meanings, units, aliases) | ❌ | Raw schema only |
| MCP integration | ❌ | Direct SQLAlchemy; no MCP registry |
| Web research / document intelligence / geospatial / NLP / ML / forecasting / A-B / causal | ❌ | Nothing implemented |

## B. Data types the system can work with today

| Type | Status | Via |
|---|---|---|
| Relational databases (Postgres, BigQuery, SQLite) | ✅ | `connections` + `schema_inspector` |
| CSV/Excel/Parquet/JSON files | ❌ | No upload path exists |
| PDF/DOCX/HTML/MD documents | ❌ | No parser, no RAG |
| Time-series columns | 🟡 | Can aggregate/filter via SQL; no dedicated forecasting workflow |
| Geospatial columns | 🟡 | Treated as ordinary columns; no geo detection/maps |
| Text-heavy columns | 🟡 | Treated as ordinary columns; no NLP workflows |
| Images/audio/video | ❌ | No multimodal pipeline |

## C. Specialist-role mapping (target roster → current state)

| Role | Current state | Phase (see plan) |
|---|---|---|
| Data Profiler | ❌ (schema inspector is a tool, not a profiler) | 3 |
| Data Quality Engineer | ❌ | 3 |
| SQL/Database Analyst | ✅ exists — becomes a Specialist in the registry | 4 |
| Exploratory Data Analyst | 🟡 (stats + anomalies only) | 5 |
| Statistician | ❌ | 5 |
| Visualization Expert | 🟡 (chart-type selection only) | 5/8 |
| Time-Series/Forecasting Expert | ❌ | 5/9 |
| Experimentation/A-B Expert | ❌ | 9 |
| Causal Analysis Expert | ❌ | 9 |
| Machine Learning Scientist | ❌ | 9 |
| Anomaly/Fraud Expert | 🟡 (z-score/IQR on single results) | 5/9 |
| NLP Expert | ❌ | 9 |
| Geospatial Analyst | ❌ | 9 |
| Document Intelligence Analyst | ❌ | 6/9 |
| Multimodal Analyst | ❌ | 9 (extension layer only) |
| Data Engineer | ❌ | 3 (ingestion layer) |
| Dashboard/BI Expert | ❌ | 8 |
| Research/Fact-Finding Agent | ❌ | 9 (only if a real retrieval source exists) |
| Reporting/Storytelling Agent | 🟡 (InsightAgent narrates one analysis) | 8/10 |

Rule honored throughout the plan: a role with ❌ stays ❌ in the product until
its workflow actually executes — no persona labels without backing capability.
