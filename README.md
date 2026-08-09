# StoryGen

AI-powered software delivery planning tool that turns BRDs into features, stories, story points, and test cases — with human review at every step.

## Overview

StoryGen ingests Business Requirement Documents (PDF, DOCX, XLSX) and runs them through a structured AI pipeline:

1. Feature extraction (chunk-aware; cross-BRD near-duplicate warnings)
2. Sub-feature generation
3. User story generation (BRD-grounded + cross-BRD dedup context)
4. Story point estimation (RAG-calibrated when history exists)
5. Test case generation
6. Export — CSV, Jira import CSV, or Markdown

Each stage supports edit, approve, reject, and reopen before the next stage runs. The React workspace is task-first: pipeline stepper, review queue, structure tree, and jobs drawer. Approving advances to the next queue item (or suggests the next stage); export shows readiness counts before download; linked BRD chunks open from source grounding.

## Tech stack

### Backend

- Python 3.13+
- FastAPI (async REST)
- SQLAlchemy async + Alembic
- PostgreSQL (+ pgvector for embeddings / RAG)
- OpenAI SDK (chat + embeddings)
- Docling (BRD parse)
- uv (deps / env)

### Frontend

- React 19 + Vite
- Plain CSS (no Tailwind)
- React Router

## Project structure

```
StoryGen/
├── architecture/          # plans and design notes
├── backend/
│   ├── alembic/
│   ├── app/
│   │   ├── ai/            # prompts, nodes, graphs, chunking, RAG
│   │   ├── api/v1/        # routers
│   │   ├── core/
│   │   ├── db/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   └── services/
│   ├── samples/
│   ├── scripts/           # seed_demo.py
│   └── tests/
├── frontend/
│   └── src/
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
cd StoryGen
uv sync --group dev
cp backend/.env.example backend/.env
# Edit DATABASE_URL, SECRET_KEY, OPENAI_API_KEY
# Keep AUTH_DISABLED=false unless you intentionally want local auth bypass

cd backend
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

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
- Forgot password sends a reset email when `SMTP_HOST` is set (link uses `FRONTEND_BASE_URL`). With `DEBUG=true` and no SMTP, the reset link is logged and `reset_token` is returned in the API response for `/reset-password`.
- Admins see **Ops** in the header (`/admin/operations`) for cross-user async job cancel/retry.
- With `AUTH_DISABLED=true` and `DEBUG=true`, Bearer auth is bypassed for local convenience — do not use in production.

## AI pipeline flow

```
BRD upload & parse (+ chunk index / embeddings)
    → features (review; cross-BRD similar warnings)
    → sub-features (review)
    → stories (review; BRD chunk grounding + cross-BRD similar)
    → story points (review; RAG calibration)
    → test cases (review)
    → export CSV / Jira CSV / Markdown
```

Long-running steps return **202** `{ operation_id }` and are polled (or streamed via SSE) in the jobs UI.

## Tests

```bash
uv run pytest
```

## Demo seed (local)

```bash
PYTHONPATH=backend uv run python backend/scripts/seed_demo.py
```

Creates `demo@storygen.local` / `demo12345` and a **Sample Payments BRD** with a small approved pipeline (plus one pending feature). Sample Markdown also lives at `backend/samples/sample_brd.md`.

## Docs

Design / handoff notes live in `architecture/`:

- [PROJECT_SUMMARY.md](architecture/PROJECT_SUMMARY.md) — current status + next work
- [AI_PIPELINE_PLAN.md](architecture/AI_PIPELINE_PLAN.md) — AI layer design and phase status
- [IMPROVEMENTS.md](architecture/IMPROVEMENTS.md) — prioritized backlog
- [FRONTEND_UX_PLAN.md](architecture/FRONTEND_UX_PLAN.md) — review workspace design
- [PROJECT_STRUCTURE.md](architecture/PROJECT_STRUCTURE.md) — folder map and full API list

## Operational notes

- **Rate limits** (in-memory, per IP): auth `20/min`, upload `10/min`, AI enqueue `30/min`. Disable with `RATE_LIMIT_ENABLED=false`.
- **Security headers** are set on all responses (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`).
- **Async jobs** use in-process `BackgroundTasks`. On restart, stuck `pending`/`running` ops are marked failed so you can retry from Ops / the workspace.
- Upload size is capped by `MAX_UPLOAD_SIZE_MB` (default 20).

## Best practices

- Do not commit `.env`
- Prefer `uv add` over bare `pip install`
- Commit `uv.lock`
- Keep API → services → repositories → DB separation

## Author

Suraj Biswas
