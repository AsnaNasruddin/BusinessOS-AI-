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
| Frontend data | ✅ Mostly wired to the real API now (Dashboard, Runs, Agents, Knowledge Base, Approvals, and any real workflow at `/workflows/:id`). What's left on placeholder/mock data: the bare `/workflows` route (a fixed example canvas kept for the original visual design, superseded by `/workflows/:id` for anything real) and the top bar's ambient "3 running · tok/min" status. `frontend/src/lib/seed-data.ts` still backs those two. |
| Backend skeleton (Phase 0) | ✅ Built (`backend/`) — FastAPI hello-world, async SQLAlchemy + Alembic wired, Celery worker skeleton, Docker Compose, CI. No business logic yet — that's Phase 1+. |
| Auth + Orgs (Phase 1) | ✅ Built — JWT access/refresh, bcrypt, org create/list/invite/accept-invite, org-scoped membership enforcement. Frontend wired (login/register/org switcher). |
| Tools + LLM abstraction (Phase 2) | ✅ Built — Agent CRUD (org-scoped), built-in tool registry, unified LLM provider interface (Ollama + Anthropic/OpenAI/Groq over plain HTTPS). Verified with a real completion through Ollama (`llama3.1:8b`, running locally via `brew services`). Frontend Agents page wired to the real API. |
| Knowledge Base / RAG (Phase 3) | ✅ Built — KB + document CRUD, real ingestion pipeline (chunk → embed via Ollama `nomic-embed-text` → store in Chroma), retrieval endpoint. Seeded with all 11 real `seed-data/knowledge-base/` docs across 3 KBs; verified with a live semantic query returning correct, relevant chunks. Frontend KB page wired to the real API (read path only — upload UI still a placeholder). Only plain-text formats (.md/.txt/.html) are parsed so far, not PDF/DOCX. |
| Workflow engine v0 (Phase 4) | ✅ Built — Workflow/Run/Step models, a graph validator (`app/workflows/graph.py`), a real execution engine dispatching trigger/agent/tool/end nodes, Celery-backed async runs. `search_kb` tool nodes run the real Phase 3 RAG pipeline; other tools are honest stubs (no email/CRM/HTTP integrations exist yet). Verified via the real API → Celery → worker path, not just direct calls. |
| Branches + approvals (Phase 5) | ✅ Built — the graph validator now accepts `condition` (evaluates a field/operator/value against the run's context, picks one of two edges), `parallel`/`merge` (fan-out to N branches, a matched `merge` joins them — structurally required to trace back to the same `parallel` node, so a run can never hang waiting on a branch a `condition` didn't take), and `approval` (pauses the run, snapshots its context/state to the DB). `POST /approvals/{id}/decide` either resumes execution via a new Celery task or ends the run — same commit-before-enqueue pattern as triggering a run. Found and fixed a real bug along the way: a Celery worker processing a second async task in the same process crashed with an asyncpg "attached to a different loop" error, since each task gets its own `asyncio.run()` loop but the DB engine's connection pool was created once at import time — fixed by disposing the pool after every task. Frontend Approvals page wired to the real API, including the Approve/Reject buttons (previously present but not actually calling the backend). Verified end-to-end through the real API → Celery → worker path for both the pause and the resume. |
| Memory (Phase 6) | ✅ Built — a durable `AgentMemory` table (org + free-text subject, e.g. a customer name) that survives across separate workflow runs, unlike the per-run `context` dict Phases 4/5 already had. Two new real tool nodes: `remember_fact` and `recall_memories`, both resolving dot-paths into context (the same syntax Phase 5's `condition` nodes use) rather than needing agents to call tools directly — that prerequisite (a real tool-calling loop) still doesn't exist. Verified by running the same workflow twice for the same customer: the second run's `recall_memories` step genuinely sees what the first run wrote, through the database, with a completely fresh execution context each time — not shared in-memory state. Also fixes the long-standing Runs page gap (Phase 4-5): it's wired to a real `GET /runs` endpoint now, listing every real run with a working list-and-detail view, instead of pointing at a single hardcoded id. |
| Natural Language Workflow Generator (Phase 7) | ✅ Built — describe a workflow in plain English, answer clarifying questions if the planner has any, review a plain-English preview, and it lands as a real (inactive) `Workflow` row through the exact same graph validator manual workflows use. Two new prerequisites this needed and didn't exist before: structured JSON-schema-constrained output and a real bounded tool-calling loop (`app/agents/executor.py`) for the LLM layer, since agents previously only ever did single-shot completions. The planner is an ordinary `Agent` row with three real read-only tools (`list_agents`/`list_tools`/`list_knowledge_bases`) it calls itself, mid-reasoning — verified live against Ollama, including a genuine round-trip (tool call → real result fed back → final answer). The IR-to-graph compiler is pure, deterministic Python (no LLM), unit-tested, and bridges a couple of the addendum's original assumptions to what Phases 4-5 actually built (e.g. condition nodes use a real `{field, operator, value}` shape, not a `simpleeval` expression string). Natural-language editing of existing workflows (diff → review → apply/reject) is fully built end to end, backend and frontend (Phase 8 wired the UI). Frontend: a single-page "describe → clarifying questions → preview → review" wizard, and the Workflow Builder canvas now also renders a real generated graph (read-only — full drag/save editing of real workflows remains separate follow-up work). See [`docs/`](docs/) for the original spec. |
| Close known UX gaps (Phase 8) | ✅ Built — three real gaps closed. **Cost tracking**: agent steps now estimate real USD cost from a per-provider blended token rate (`app/llm/pricing.py`; Ollama is always $0, unknown cloud models honestly report $0 rather than guessing), accumulated into `WorkflowRun.total_cost_usd` the same way `total_tokens` already was. **Dashboard**: `GET /dashboard/stats` computes real org-scoped aggregates (active/total workflows, runs in the last 24h, 7-day success rate, 30-day tokens + cost with a human-readable cost note) and the frontend Dashboard page now renders it instead of mock data. **NL-edit frontend**: `NlEditBar` + `NlEditDiffCard` wire the Workflow Builder's canvas up to the natural-language edit backend Phase 7 already had — type an instruction, review a real diff, apply or reject it, and the canvas re-renders live (no reload) once applied. Along the way, live end-to-end testing surfaced and fixed two real bugs left over from Phase 7. First, the planner prompt never explained edit-mode semantics, so the LLM would sometimes reference an existing node by its label directly instead of re-declaring it with a fresh `ref`, and the compile would fail — the prompt now spells out the rule explicitly. Second, and more fundamental: the Workflow Planner agent the NL generator depends on only ever existed for orgs `scripts/seed_dev_data.py` had been run against — a brand-new user registering for the first time got a completely empty org and could never generate a workflow at all, with no manual "create workflow" UI to fall back on either. Fixed by seeding a Workflow Planner into `org_service.create_org` itself (`ensure_planner_agent`, in `app/workflow_generation/planner.py`) — the one choke point every org-creation path (registration, and the standalone `POST /orgs` for a second org) already goes through, so no org is ever silently missing it. Verified against the real running stack with a brand-new, never-seeded user end to end. |

The frontend is real, runnable code, and by now most of it is wired to the real
backend rather than seed data — see the "Frontend data" row above for exactly
what's left on mocks.

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
1. ✅ Auth + Orgs
2. ✅ Tools + LLM abstraction
3. ✅ Knowledge Base (RAG)
4. ✅ Workflow engine v0 (linear execution)
5. ✅ Branches + approvals
6. ✅ Memory (+ the Runs page fix)
7. ✅ **Natural Language Workflow Generator** *(see docs/)*
8. ✅ Close known UX gaps *(real cost tracking, real Dashboard, NL-edit frontend)*

Frontend scaffolding (this repo's current state) sits ahead of the backend phases
that would normally gate it — the visual design was built and approved first, then
translated into real components against placeholder data so the UI itself could be
reviewed before the engine exists underneath it.
