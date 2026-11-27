# MetricTrace

MetricTrace is a time-travel debugger for business metrics that reproduces
historical results, separates data changes from metric-definition changes,
validates business contracts and preserves verifiable evidence behind
decisions.

This repository is being migrated from the original Decision Intelligence
Agent. The first MetricTrace vertical slice is real and deterministic: it
publishes immutable local Parquet snapshots, executes versioned metric SQL in
DuckDB, runs all four data/definition combinations, and reconciles the change.
It does not require AI credentials.

## Try the canonical replay

1. Start the backend and frontend below.
2. Sign in (or use the existing local development auth setup).
3. Open **Replay Lab** and choose **Run canonical replay**.
4. Inspect the four execution cells and the data, definition and interaction
   effects. The fixture shows ₹24 lakh for original Monday data and ₹18 lakh
   after a corrected marketplace order using the original definition.

Historical storage defaults to `backend/metrictrace-history` for local work.
Mount durable storage or replace the local adapter before hosting it.

## Implemented MetricTrace capabilities

- tenant-scoped workspace metadata and membership records;
- immutable Parquet data versions with hash manifests;
- immutable, versioned metric SQL definitions;
- SQLGlot read-only validation and DuckDB historical execution;
- four-way replay with exact per-cell input IDs and symmetric attribution;
- deterministic replay fixture and an interactive Replay Lab.

See [the product specification](docs/PRODUCT_SPEC.md), [migration plan](docs/MIGRATION_PLAN.md), and [baseline audit](docs/BASELINE_AUDIT.md) for the implementation boundary and next work.

## Existing analysis features

The retained legacy application supports:

- intent classification
- task planning
- SQL generation and correction
- execution against a user database
- statistical analysis and anomaly detection
- hypothesis validation
- human-readable insight synthesis
- deterministic chart recommendations and multi-panel visual dashboards
- direct specialist forms for text, lists, numeric inputs, and CSV table data (no JSON required)

The repo is structured as a monorepo with:

- `backend/` - FastAPI service, agent pipeline, DB models, migrations, and tests
- `frontend/` - Next.js app with chat, results, schema exploration, and history views

## Local Setup

### Backend

```bash
cd backend
cp .env.example .env
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Frontend env notes:
- Leave `NEXT_PUBLIC_API_URL` empty to use the built-in Next.js `/api/*` proxy.
- Set only server-side `BACKEND_API_URL` to the FastAPI origin the proxy should forward to.
- For local development, use `BACKEND_API_URL=http://127.0.0.1:8000`.
- For Vercel, leave browser traffic on the same origin and set `BACKEND_API_URL` to your Render service URL (for example, `https://your-service.onrender.com`). Do not set a `NEXT_PUBLIC_BACKEND_API_URL`.
- Only set `NEXT_PUBLIC_USE_DIRECT_API=true` if you intentionally want the browser to call the backend origin directly.

## Notes

- SQLite is supported for local development only. Set `DATABASE_URL` to a managed PostgreSQL URL in Render; the application refuses to start in production with SQLite, preventing accidental loss of users, connections, and history on Render's ephemeral filesystem.
- Dataset uploads are temporary working files stored under `/tmp`; they are intentionally not advertised as durable storage and will be unavailable after a Render restart. Use a connected database for durable analysis.
- To use OpenAI-backed agents, set `OPENAI_API_KEY` in `backend/.env`. The backend already prefers OpenAI automatically when that key is present.
- Core chart selection, dashboard assembly, simulation, evaluation, and specialist execution are deterministic and do not require OpenAI. This keeps API use focused on tasks where generated reasoning adds value.
- For Neon connections, keep `ssl_mode=require` and use the database password from Neon connection details. The app now validates credentials before saving a connection.

## Deployment

Architecture: browser → Vercel Next.js `/api/*` proxy → Render FastAPI → managed PostgreSQL / AI provider.

### Render

Create a web service from `render.yaml`. Set `DATABASE_URL` to the managed PostgreSQL connection URL and `OPENAI_API_KEY` if OpenAI-backed responses are required. Set `ALLOWED_ORIGINS` to your local and production frontend origins. The container respects Render's `PORT`, uses one Uvicorn worker, and uses a conservative primary-database pool (2 connections plus one overflow). `GET /health` is a lightweight liveness check.

The managed PostgreSQL database stores application state and session history. No Redis, Chroma, worker service, document-retrieval service, or additional Render service is required.

Run migrations as a one-off release/manual command before the first deploy:

```bash
cd backend
alembic upgrade head
```

### Vercel

Import `frontend/` as the Vercel project root. Set `BACKEND_API_URL=https://your-render-service.onrender.com` in Vercel's server-side environment variables, plus the Clerk values already required by the app. Do not expose backend URLs, database URLs, or provider keys through `NEXT_PUBLIC_*`. The catch-all proxy preserves request methods, status codes, headers, and streaming response bodies.
