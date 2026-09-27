# Codebase audit — single Render service

## Runtime shape

The deployed application is one Render web service plus its managed PostgreSQL
database. `render.yaml` keeps agent concurrency at one and bounds query,
schema, specialist, and RAG workloads for a 512 MB instance. No worker,
Redis, Chroma, MCP, or additional Render service is required.

## Removed unreachable code

- `backend/app/mcp/`: no API route, agent, or runtime module imported it.
- `backend/app/dashboard/`: duplicate dashboard models and assembler; the live
  pipeline already uses `specialists/dashboard_specialist.py`.
- `backend/app/workers/`, `worker_client.py`, and `render.workers.yaml`: an
  optional multi-service design that conflicts with the single-service target.
- `core/planning.py` and `services/embedding_service.py`: re-export-only code
  with no runtime consumers.
- Chroma and Redis fallback paths: dependencies were not installed and neither
  was configured for the deployment.

## Production logic retained and corrected

- RAG chunks persist in `rag_document_chunks` in the existing application
  database. Retrieval is user-scoped and ranks at most the configured candidate
  limit in memory.
- Session context reads completed `QueryHistory` rows from the app database,
  rather than relying on ephemeral disk or an absent Redis service.
- Diagnostic fallback hypotheses no longer run a misleading `SELECT 1`.
  They are emitted as unvalidated until a schema-grounded query is available.
- Dashboard panels preserve the recommender's `chart_type`; their streamed
  specialist result is retained in frontend state and rendered alongside query
  evidence. Pie, scatter, table, and numeric-string chart paths are handled.

## Verification

- Backend: `pytest -q` — 196 passed.
- Frontend: `npx tsc --noEmit` and `npm run build` completed successfully.
