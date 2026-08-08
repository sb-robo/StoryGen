# StoryGen

AI-powered software delivery planning tool that turns BRDs into features, stories, story points, and test cases — with human review at every step.

## Overview

StoryGen ingests Business Requirement Documents (PDF, DOCX, XLSX) and runs them through a structured AI pipeline:

1. Feature extraction  
2. Sub-feature generation  
3. User story generation  
4. Story point estimation (RAG-calibrated when history exists)  
5. Test case generation  
6. CSV / Jira import CSV export  

Each stage supports edit, approve, reject, and reopen before the next stage runs.

## Tech stack

### Backend

- Python 3.13+
- FastAPI (async REST)
- SQLAlchemy async + Alembic
- PostgreSQL (+ pgvector for embeddings)
- OpenAI SDK (chat + embeddings)
- Docling (BRD parse)
- uv (deps / env)

### Frontend

- React 19 + Vite
- Plain CSS (no Tailwind)
- React Router

### Optional / deferred

- `streamlit_app/` — placeholder for a future prompt lab (not wired yet)

## Project structure

```
storygen/
├── architecture/          # plans and design notes
├── backend/
│   ├── alembic/
│   └── app/
│       ├── ai/            # agents, prompts, RAG helpers
│       ├── api/v1/        # routers
│       ├── core/
│       ├── db/
│       ├── repositories/
│       ├── schemas/
│       └── services/
├── frontend/
│   └── src/
├── streamlit_app/         # empty / deferred
├── docker-compose.yml     # local Postgres (+ pgvector)
├── pyproject.toml
└── README.md
```

## Setup

### Prerequisites

- Python 3.13+
- Node.js 18+
- PostgreSQL with pgvector (easiest: `docker compose up -d` from repo root)
- [uv](https://docs.astral.sh/uv/)

### Backend

```bash
cd storygen
uv sync --group dev
cp backend/.env.example backend/.env
# Edit DATABASE_URL, SECRET_KEY, OPENAI_API_KEY
# Keep AUTH_DISABLED=false unless you intentionally want local auth bypass
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --app-dir backend
```

Or from `backend/` with `PYTHONPATH` set appropriately — the repo root `pyproject.toml` already points pytest at `backend/`.

- API: http://localhost:8000  
- Docs: http://localhost:8000/docs  
- Health: http://localhost:8000/health  

### Frontend

```bash
cd frontend
npm install
npm run dev
```

- UI: http://localhost:5173  

Set `VITE_API_ORIGIN` if the API is not on the same host (defaults to relative `/api/v1` via Vite proxy if configured).

## Auth notes

- Register / login / refresh / logout are implemented.
- Forgot password returns a `reset_token` only when `DEBUG=true` (no email sender yet). Use that token on `/reset-password`.
- With `AUTH_DISABLED=true` and `DEBUG=true`, Bearer auth is bypassed for local convenience — do not use in production.

## AI pipeline flow

```
BRD upload & parse
    → features (review)
    → sub-features (review)
    → stories (review)
    → story points (review)
    → test cases (review)
    → export CSV / Jira CSV
```

## Tests

```bash
uv run pytest
```

## Best practices

- Do not commit `.env`
- Prefer `uv add` over bare `pip install`
- Commit `uv.lock`
- Keep API → services → repositories → DB separation

## Author

Suraj Biswas
