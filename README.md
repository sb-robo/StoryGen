# 🚀 StoryGen

> AI-powered software delivery planning tool that transforms BRDs into features, Jira stories, and test cases — with human review at every step.

---

## 📌 Overview

StoryGen is a full-stack AI-powered platform that ingests Business Requirement Documents (BRDs) and processes them through a structured, multi-step AI pipeline.

It generates:

* Features & sub-features
* User stories
* Story points
* Test cases

Each stage includes **human-in-the-loop validation**, ensuring accuracy, control, and production usability.

---

## 🛠️ Tech Stack

### Backend

* **Python 3.12+**
* **FastAPI** — async REST APIs
* **SQLAlchemy (async)** — ORM
* **Alembic** — migrations
* **PostgreSQL** — relational + vector-ready storage
* **LiteLLM** — LLM abstraction (Azure GPT-4o)
* **uv** — dependency & environment manager

### AI Layer

* Agent-based orchestration
* Graph-based execution pipelines
* RAG (Retrieval-Augmented Generation)
* Prompt engineering modules
* Stateful workflow management

### Frontend

* **React (Vite)**
* **Tailwind CSS**

### Dev Tooling

* **Streamlit** — internal testing & rapid AI prototyping

---

## 📂 Project Structure

```
storygen/
├── architecture/
│   └── PROJECT_STRUCTURE.md
├── backend/
│   ├── alembic/
│   │   ├── README
│   │   ├── env.py
│   │   └── script.py.mako
│   ├── app/
│   │   ├── ai/
│   │   │   ├── agents/
│   │   │   ├── graphs/
│   │   │   ├── nodes/
│   │   │   ├── prompts/
│   │   │   ├── rag/
│   │   │   └── states/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       └── routers/
│   │   ├── core/
│   │   ├── db/
│   │   │   └── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── utils/
│   │   └── main.py
│   └── alembic.ini
├── frontend/
│   ├── public/
│   └── src/
│       └── assets/
├── streamlit_app/
│   └── app.py
├── .python-version
├── .gitignore
├── pyproject.toml
└── README.md
```

---

## ⚙️ Setup Instructions

### Prerequisites

* Python 3.12+
* Node.js 18+
* PostgreSQL (running locally)
* `uv` installed → https://docs.astral.sh/uv/

---

## 🔧 Backend Setup

```bash
git clone <your-repo-url>
cd storygen/backend
```

### Install dependencies

```bash
uv sync
```

### Create `.env`

```env
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/storygen
```

### Run migrations

```bash
uv run alembic upgrade head
```

### Start server

```bash
uv run uvicorn app.main:app --reload
```

* API → http://localhost:8000
* Docs → http://localhost:8000/docs

---

## 💻 Frontend Setup

```bash
cd storygen/frontend
npm install
npm run dev
```

* UI → http://localhost:5173

---

## 🧪 Streamlit (Internal Tooling)

```bash
cd storygen/streamlit_app
uv run streamlit run app.py
```

Used for:

* Testing AI pipelines
* Debugging prompts
* Rapid prototyping

---

## 🗄️ Database

* PostgreSQL with async driver (`asyncpg`)
* Supports:

  * Relational data
  * Vector embeddings (for RAG)
* Managed via Alembic migrations

### Commands

```bash
uv run alembic revision --autogenerate -m "message"
uv run alembic upgrade head
```

---

## 🔄 AI Pipeline Flow

```
BRD Upload
    ↓
Feature Extraction (AI)
    ↓
Review & Edit (Human)
    ↓
Sub-feature Generation (AI)
    ↓
Review & Edit (Human)
    ↓
Story Generation (AI)
    ↓
Review + Story Points (Human)
    ↓
Export → Jira / CSV
```

---

## 🧪 Running Tests

```bash
cd backend
uv run pytest
```

---

## 📌 Best Practices

* Do not commit `.env`
* Use `uv add` instead of `pip install`
* Commit `uv.lock` for reproducibility
* Keep AI logic modular inside `app/ai`
* Maintain strict separation:

  * API → Services → Repositories → DB

---

## 👨‍💻 Author

**Suraj Biswas**
