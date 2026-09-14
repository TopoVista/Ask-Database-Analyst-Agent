# Isolated 512 MB Render workers

The main API remains responsible for Clerk authentication, user scoping, and
database credentials. Resource-intensive specialist actions and document RAG
can be moved to independently deployed Render web services, each on the
`free` (512 MB) plan.

## What is isolated

- `time_series_forecaster` — forecast and decomposition calculations.
- `ml_scientist` and `causal_analyst` — model fitting and effect analysis.
- `anomaly_advanced` — row/column anomaly scoring.
- `nlp_text_analyst` — larger text-column analysis jobs.
- RAG — PDF parsing, chunking, embedding, retrieval, and durable chunk search.

Dashboard assembly and the deterministic simulation/evaluation paths stay in
the main API because they are already small, bounded operations.

## Deployment

1. Deploy the main API from `render.yaml`.
2. In Render, create a second Blueprint deployment using
   `render.workers.yaml`. It contains one 512 MB web service for each listed
   worker. Keep them in the same Render region.
3. Set an identical long random `WORKER_SHARED_TOKEN` secret on the main API
   and every worker. Worker endpoints reject all requests without that token.
4. Give `di-rag-worker` the same managed Postgres `DATABASE_URL` as the main
   API. Its `RAG_STORE_BACKEND=database` setting persists chunks in
   `rag_document_chunks`; it does not rely on an ephemeral Render disk.
5. Copy each worker's Render private URL into the main service:

   ```text
   RAG_WORKER_URL=http://di-rag-worker:10000
   SPECIALIST_WORKER_URLS=time_series_forecaster=http://di-forecast-specialist:10000,ml_scientist=http://di-model-specialist:10000,causal_analyst=http://di-model-specialist:10000,anomaly_advanced=http://di-anomaly-specialist:10000,nlp_text_analyst=http://di-nlp-specialist:10000
   ```

   If private DNS is unavailable for the selected Render plan, use each
   worker's HTTPS public URL instead; the shared token remains mandatory.

## Resource guarantees and limits

The Blueprint uses exactly one Uvicorn worker per service, Render's `free`
512 MB plan, and bounded input sizes (200–250 rows for specialists, 4 MB
documents, 100 chunks/document, and 500 RAG candidates/search). Those bounds
are designed to keep normal workloads inside 512 MB; no software can promise
an absolute memory ceiling if a runtime/library itself exceeds it. Do not add
PyTorch, TFT, or local LLM weights to these services. Put such models behind a
managed inference endpoint or upgrade only their dedicated worker.
