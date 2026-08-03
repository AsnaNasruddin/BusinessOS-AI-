# BusinessOS AI

> Windows manages applications. BusinessOS manages AI employees.

A modular, open-source platform that lets any business build AI-powered workflows —
email triage, document processing, approvals, RAG-based Q&A — by wiring together
reusable building blocks (agents, tools, knowledge bases, human approvals) instead of
writing custom code for every automation.

Personal learning project. Not a paid client project. Planned license: **MIT**.

## Status

This repo is early — here's what actually exists today versus what's planned:

| Piece | Status |
|---|---|
| Frontend shell, design system, routing | ✅ Built (`frontend/`) — Dashboard, Workflow Builder, Agents, Knowledge Base, Runs, Approvals, Login |
| Frontend data | ⚠️ Seeded/placeholder — every screen reads from `frontend/src/lib/seed-data.ts`, not a live API |
| Backend skeleton (Phase 0) | ✅ Built (`backend/`) — FastAPI hello-world, async SQLAlchemy + Alembic wired, Celery worker skeleton, Docker Compose, CI. No business logic yet — that's Phase 1+. |
| Auth, Agents, KB, Workflow engine, Approvals, Memory (Phases 1–6) | ⏳ Not started |
| Natural Language Workflow Generator (Phase 7) | 📝 Spec'd, not built — see [`docs/`](docs/) |

The frontend is real, runnable code — it's just not wired to anything yet. Every
`TODO(learning)` comment in `frontend/src/hooks/` marks exactly where a live API
call replaces the seed data once the backend has something to call.

## Quick start

```bash
# Frontend
cd frontend
pnpm install
pnpm dev                          # → http://localhost:5173

# Backend (Phase 0 — hello-world only, no real endpoints yet)
cd backend
python3.11 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn app.main:app --reload   # → http://localhost:8000/docs
.venv/bin/pytest                          # → 4 passing
.venv/bin/ruff check .

# Everything together via Docker Compose (requires Docker — not verified in
# this environment; see the note in docker-compose.yml before first run)
cp .env.example .env
docker compose up -d
```

See [`frontend/README.md`](frontend/README.md) and [`backend/README.md`](backend/README.md)
for the full script lists and env vars.

## The mental model

You are not building a chatbot. You are not building one automation. You are
building an **AI Operating System** where workflows are the "programs" and agents
are the "runtime."

Two ways to build a workflow, landing in the same place:

- **Visual Workflow Builder** — drag-and-drop nodes (trigger, agent, tool,
  condition, approval, parallel, merge, end) on a React Flow canvas, for technical
  users.
- **Natural Language Workflow Generator** *(planned)* — describe the process in
  plain English; the AI drafts the same kind of workflow for review before
  activation. See the [ADR](docs/adr/0001-natural-language-workflow-generator.md).

Both paths produce the exact same underlying workflow graph. Neither bypasses human
review before a workflow goes live.

## Technology stack

| Layer | Choice |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Alembic, Celery + Redis |
| Frontend | React 18, Vite, TypeScript, Tailwind CSS, React Flow, Zustand, TanStack Query |
| AI / ML | Local LLMs via Ollama by default; Anthropic/OpenAI/Groq optional behind one `LLMClient` interface; ChromaDB for vectors; sentence-transformers for embeddings |
| Data | SQLite (dev) / PostgreSQL 16 (prod), Redis, local FS / MinIO for uploads |
| Infra | Docker Compose, GitHub Actions CI, ruff (Python) + eslint/prettier (TS) |

No paid API keys are required to run the project. Everything works against a local
Ollama model; cloud providers are opt-in.

## Repository layout

```
businessos-ai/
├── README.md              ← you are here
├── docker-compose.yml      postgres, redis, chromadb, backend, worker, frontend
├── .env.example
├── docs/
│   ├── adr/                          architecture decision records
│   └── implementation-plan-addendum-nl-workflow-generator.md
├── docker/                 backend.Dockerfile, frontend.Dockerfile, worker.Dockerfile
├── scripts/                 reset_db.sh, seed_dev_data.py
├── seed-data/                fake company data (Acme Robotics) — see seed-data/README.md
├── frontend/                  React + Vite + TypeScript app (see frontend/README.md)
├── backend/                    FastAPI + Celery app, Phase 0 skeleton (see backend/README.md)
└── .github/workflows/ci.yml     ruff + pytest, eslint + build
```

## Documentation

- **Implementation Plan v1.0** — the source-of-truth spec for architecture, data
  model, module breakdown, API design, and development phases. Referenced
  throughout this codebase and its docs; not yet checked into this repo as a file.
- [`docs/adr/0001-natural-language-workflow-generator.md`](docs/adr/0001-natural-language-workflow-generator.md)
  — decision record for the natural-language workflow creation/editing layer.
- [`docs/implementation-plan-addendum-nl-workflow-generator.md`](docs/implementation-plan-addendum-nl-workflow-generator.md)
  — full spec for that feature: data model, structured output schemas, API design,
  validation pipeline, and the section-by-section diff against the base plan.
- [`seed-data/README.md`](seed-data/README.md) — the fake Acme Robotics company data
  (policies, product docs, sample emails/invoices) used across every demo, and how
  it maps onto the `Organization`/`KnowledgeBase`/`Document` data model.

Further ADRs land in `docs/adr/` as new architectural decisions come up — see the
addendum's own Rule 13/14 additions for the standing convention.

## Development phases

0. ✅ Skeleton — repo layout, Docker Compose, CI
1. Auth + Orgs
2. Tools + LLM abstraction
3. Knowledge Base (RAG)
4. Workflow engine v0 (linear execution)
5. Branches + approvals
6. Memory + observability
7. **Natural Language Workflow Generator** *(new — see docs/)*
8. Polish + docs

Frontend scaffolding (this repo's current state) sits ahead of the backend phases
that would normally gate it — the visual design was built and approved first, then
translated into real components against placeholder data so the UI itself could be
reviewed before the engine exists underneath it.
