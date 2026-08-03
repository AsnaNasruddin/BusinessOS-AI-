# BusinessOS AI — Backend

FastAPI + async SQLAlchemy + Celery backend for BusinessOS AI. See the
[project root README](../README.md) for the overall product and architecture, and
[`../docs/`](../docs/) for the implementation plan and its addenda.

## Status: Phase 0 (Skeleton)

What exists right now:

- A FastAPI app that boots and serves `/`, `/health`, and the auto-generated
  `/docs` — nothing else yet.
- Async SQLAlchemy 2.0 wired to a `Base` with zero models (Phase 1 adds the
  first ones: `User`, `Organization`, `Membership`).
- Alembic configured and runnable (`alembic upgrade head` currently applies
  zero migrations — there's nothing to migrate yet).
- A Celery app with one trivial `ping` task, proving the worker container has
  a working entrypoint.
- `ruff check` / `ruff format --check` and `pytest` both pass (4 tests, all
  around the hello-world endpoints and settings — real endpoint tests start
  in Phase 1).

Nothing here does anything useful yet — that's the point of a skeleton phase.
See the [root README's phase table](../README.md#development-phases) for
what's next.

## Local development (without Docker)

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev]"

.venv/bin/uvicorn app.main:app --reload    # → http://localhost:8000/docs
.venv/bin/pytest                            # run tests
.venv/bin/ruff check .                      # lint
.venv/bin/ruff format .                     # format
.venv/bin/alembic upgrade head              # apply migrations (none yet)
```

Defaults to a local SQLite file (`businessos.db`, gitignored) and expects
Redis/Chroma to be unavailable — nothing in Phase 0 calls them yet.

## Via Docker Compose

From the repo root:

```bash
cp .env.example .env
docker compose up -d
docker compose exec backend alembic upgrade head
```

This has not been verified in the environment this backend was scaffolded in
(no Docker available there) — the compose file's YAML has been validated for
syntax, and the Dockerfiles follow standard patterns, but give it a real run
before trusting it blindly.

## Tech stack

Python 3.11+ · FastAPI · SQLAlchemy 2.0 (async) · Alembic · Pydantic v2 +
pydantic-settings · Celery + Redis · python-jose + bcrypt (Phase 1) · pytest +
pytest-asyncio + httpx · ruff.

## Structure

```
app/
├── main.py              FastAPI entry point
├── config.py             pydantic-settings — every env var lives here
├── deps.py                shared FastAPI dependencies
├── api/v1/                 route modules, one per resource (empty until Phase 1+)
├── database/
│   ├── session.py            async engine + session factory
│   └── models/                 SQLAlchemy models (empty until Phase 1+)
├── schemas/                Pydantic request/response models
├── services/                 business logic
├── agents/                    AgentExecutor + prompts (Phase 2)
├── llm/                         LLMClient interface + adapters (Phase 2)
├── rag/                           chunker/embedder/retriever (Phase 3)
├── tools/                           Tool base + registry + builtins (Phase 2)
├── workflows/                         graph engine (Phase 4)
├── memory/                              session/persistent memory (Phase 6)
├── worker/
│   ├── celery_app.py                      Celery app
│   └── tasks.py                              one stub `ping` task so far
└── utils/
tests/
├── unit/            e.g. test_config.py
├── integration/     e.g. test_health.py
└── conftest.py       shared fixtures (async httpx client against the app)
```
