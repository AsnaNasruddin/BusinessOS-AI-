#!/usr/bin/env python3
"""Seed the dev database with demo data — Acme Robotics (see seed-data/).

Run inside the backend container per the quickstart:
    docker compose exec backend python scripts/seed_dev_data.py

Idempotent: safe to re-run. Each step checks for existing rows by name (or,
for documents, by filename within a knowledge base) before creating
anything, so this can be run against a database that already has some or
all of the demo data in it.
"""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

from app.database.models import User
from app.database.session import async_session_maker
from app.services import auth_service, org_service

SEED_DATA_DIR = Path(__file__).parent.parent / "seed-data"

DEMO_EMAIL = "demo@businessos.ai"
DEMO_PASSWORD = "Demo1234!"
DEMO_FULL_NAME = "Jordan Avery"
DEMO_ORG_NAME = "Acme Robotics"


async def create_demo_org_and_user():
    """Phase 1 (Auth + Orgs). Creates the demo user and 'Acme Robotics' org
    from seed-data/company-profile.md — reuses either if already present."""
    async with async_session_maker() as db:
        try:
            user, _ = await auth_service.register_user(
                db, email=DEMO_EMAIL, password=DEMO_PASSWORD, full_name=DEMO_FULL_NAME
            )
            print(f"  created user {DEMO_EMAIL}")
        except auth_service.EmailAlreadyRegisteredError:
            result = await db.execute(select(User).where(User.email == DEMO_EMAIL))
            user = result.scalar_one()
            print(f"  user {DEMO_EMAIL} already exists, reusing")

        existing_orgs = await org_service.list_user_orgs(db, user=user)
        acme = next((o.org for o in existing_orgs if o.org.name == DEMO_ORG_NAME), None)
        if acme is None:
            org_with_role = await org_service.create_org(db, owner=user, name=DEMO_ORG_NAME)
            acme = org_with_role.org
            print(f"  created org '{DEMO_ORG_NAME}'")
        else:
            print(f"  org '{DEMO_ORG_NAME}' already exists, reusing")

        await db.commit()
        return acme.id


async def create_demo_agents(org_id) -> None:
    """Phase 2 (Tools + LLM abstraction). Creates the four agents already
    described in frontend/src/lib/seed-data.ts."""
    print("TODO(phase 2): create demo agents")


async def create_demo_knowledge_bases(org_id) -> None:
    """Phase 3 (Knowledge Base / RAG). Walks seed-data/knowledge-base/,
    creates one KnowledgeBase per subfolder, and runs each .md file through
    the REAL ingestion pipeline (app/rag/ingest.py) — not hand-written
    Chunk rows. See seed-data/README.md for the folder-to-KB mapping."""
    if not SEED_DATA_DIR.exists():
        print(f"seed-data/ not found at {SEED_DATA_DIR} — nothing to ingest yet.")
        return
    print("TODO(phase 3): ingest seed-data/knowledge-base/ through the real pipeline")


async def create_demo_workflows(org_id) -> None:
    """Phase 4-5 (Workflow engine + approvals). Creates the six workflows
    from frontend/src/lib/seed-data.ts, including the Customer Support
    Triage graph used throughout the design docs."""
    print("TODO(phase 4-5): create demo workflows")


async def main() -> None:
    print("Seeding BusinessOS AI dev data...")
    print("Org + user:")
    org_id = await create_demo_org_and_user()
    print("Agents:")
    await create_demo_agents(org_id)
    print("Knowledge bases:")
    await create_demo_knowledge_bases(org_id)
    print("Workflows:")
    await create_demo_workflows(org_id)
    print("Done (see TODOs above for what's not implemented yet).")


if __name__ == "__main__":
    if not (Path(__file__).parent.parent / "backend" / "app").exists():
        print("Run this from the repo root.", file=sys.stderr)
        sys.exit(1)
    asyncio.run(main())
