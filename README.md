# Decision Intelligence Agent

An autonomous decision intelligence platform that turns plain-English business questions into a multi-step analytical workflow:

- intent classification
- task planning
- SQL generation and correction
- execution against a user database
- statistical analysis and anomaly detection
- hypothesis validation
- human-readable insight synthesis

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
- Set `BACKEND_API_URL` and `NEXT_PUBLIC_BACKEND_API_URL` to the FastAPI origin the proxy should forward to.
- For local development, `http://127.0.0.1:8011` is the expected backend URL.
- For Vercel, keep browser traffic on the same origin and set `BACKEND_API_URL=https://autonomous-decision-intelligence-engine.onrender.com`.
- Only set `NEXT_PUBLIC_USE_DIRECT_API=true` if you intentionally want the browser to call the backend origin directly.

## Notes

- The backend has safe local fallbacks for OpenAI, Redis, and SQLite so the project can run in a lightweight dev setup.
- The production path still supports PostgreSQL, Clerk, Redis, Neon, Render, and Vercel as described in the architecture plan.
- To use OpenAI-backed agents, set `OPENAI_API_KEY` in `backend/.env`. The backend already prefers OpenAI automatically when that key is present.
- For Neon connections, keep `ssl_mode=require` and use the database password from Neon connection details. The app now validates credentials before saving a connection.
