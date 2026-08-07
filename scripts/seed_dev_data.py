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

from app.config import get_settings
from app.database.models import User
from app.database.session import async_session_maker
from app.rag.ingest import ingest_document
from app.schemas.agent import AgentCreate
from app.schemas.kb import KnowledgeBaseCreate
from app.services import agent_service, auth_service, kb_service, org_service

SEED_DATA_DIR = Path(__file__).parent.parent / "seed-data"

DEMO_EMAIL = "demo@businessos.ai"
DEMO_PASSWORD = "Demo1234!"
DEMO_FULL_NAME = "Jordan Avery"
DEMO_ORG_NAME = "Acme Robotics"

# Mirrors frontend/src/lib/seed-data.ts's `agents` array exactly.
DEMO_AGENTS = [
    {
        "name": "Triage Classifier",
        "description": "Classifies incoming support email.",
        "system_prompt": (
            "Classify the incoming email into billing_refund, technical_issue, or "
            "general_inquiry. Decide if knowledge-base lookup is needed. Return JSON: "
            "{category, urgency, needs_kb}."
        ),
        "model_provider": "ollama",
        "model_name": "llama3.1:8b",
        "temperature": 0.2,
        "allowed_tools": [],
        "memory_scope": "none",
    },
    {
        "name": "Draft Reply Writer",
        "description": "Writes the customer-facing reply.",
        "system_prompt": (
            "You are a support specialist for Acme Robotics. Use retrieved knowledge-base "
            "context, if any, to write a warm, precise reply. Never promise refunds outside "
            "policy. Return JSON: {subject, body, confidence}."
        ),
        "model_provider": "ollama",
        "model_name": "llama3.1:8b",
        "temperature": 0.4,
        "allowed_tools": ["search_kb", "send_email"],
        "memory_scope": "session",
    },
    {
        "name": "Memory Extractor",
        "description": "Extracts durable facts after each agent turn.",
        "system_prompt": (
            "After each agent turn, decide if anything durable happened worth remembering "
            "about this customer or deal. Return JSON: {should_remember, fact, importance}."
        ),
        "model_provider": "ollama",
        "model_name": "qwen2.5:7b",
        "temperature": 0.1,
        "allowed_tools": [],
        "memory_scope": "persistent",
    },
    {
        "name": "Lead Enrichment Agent",
        "description": "Enriches inbound leads with firmographic data.",
        "system_prompt": (
            "Given a new lead company domain, research and summarize firmographic details "
            "relevant to sales qualification. Return JSON: {company_size, industry, fit_score}."
        ),
        "model_provider": "anthropic",
        "model_name": "claude-haiku",
        "temperature": 0.3,
        "allowed_tools": ["http_request"],
        "memory_scope": "none",
    },
]

# folder under seed-data/knowledge-base/ -> (display name, description) — see seed-data/README.md
DEMO_KBS = {
    "policy-refunds": ("Policy & Refunds", "Returns, warranty, and chargeback policy."),
    "support-macros": ("Support Macros", "Canned replies and escalation scripts."),
    "product-docs": ("Product Docs", "Manuals and FAQs."),
}


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
    async with async_session_maker() as db:
        existing_names = {a.name for a in await agent_service.list_agents(db, org_id=org_id)}
        created = 0
        for spec in DEMO_AGENTS:
            if spec["name"] in existing_names:
                continue
            await agent_service.create_agent(db, org_id=org_id, data=AgentCreate(**spec))
            created += 1
        await db.commit()
        print(f"  created {created} agent(s), {len(DEMO_AGENTS) - created} already existed")


async def create_demo_knowledge_bases(org_id) -> None:
    """Phase 3 (Knowledge Base / RAG). Walks seed-data/knowledge-base/,
    creates one KnowledgeBase per subfolder, and runs each .md file through
    the real ingestion pipeline (app/rag/ingest.py) — not hand-written
    chunk rows, per seed-data/README.md."""
    kb_root = SEED_DATA_DIR / "knowledge-base"
    if not kb_root.exists():
        print(f"  {kb_root} not found — nothing to ingest.")
        return

    settings = get_settings()

    for folder_name, (display_name, description) in DEMO_KBS.items():
        folder = kb_root / folder_name
        if not folder.exists():
            print(f"  {folder} not found, skipping")
            continue

        async with async_session_maker() as db:
            existing_kbs = await kb_service.list_kbs(db, org_id=org_id)
            kb = next(
                (row_kb for row_kb, _count in existing_kbs if row_kb.name == display_name), None
            )
            if kb is None:
                kb = await kb_service.create_kb(
                    db,
                    org_id=org_id,
                    data=KnowledgeBaseCreate(name=display_name, description=description),
                )
                await db.commit()
                print(f"  created KB '{display_name}'")
            else:
                print(f"  KB '{display_name}' already exists, reusing")

            existing_filenames = {
                d.filename for d in await kb_service.list_documents(db, kb_id=kb.id)
            }

            for md_file in sorted(folder.glob("*.md")):
                if md_file.name in existing_filenames:
                    print(f"    {md_file.name} already ingested, skipping")
                    continue

                text = md_file.read_text()
                document = await kb_service.create_document(
                    db,
                    kb_id=kb.id,
                    filename=md_file.name,
                    mime_type="Markdown",
                    size_bytes=len(text.encode()),
                )
                await db.commit()

                try:
                    chunk_count = await ingest_document(
                        kb_id=kb.id,
                        document_id=document.id,
                        filename=document.filename,
                        text=text,
                        settings=settings,
                    )
                except Exception as exc:  # noqa: BLE001 - genuinely want to catch+record any failure here
                    await kb_service.mark_document_failed(db, document=document, error=str(exc))
                    await db.commit()
                    print(f"    FAILED to ingest {md_file.name}: {exc}")
                    continue

                await kb_service.mark_document_ready(db, document=document, chunk_count=chunk_count)
                await db.commit()
                print(f"    ingested {md_file.name} -> {chunk_count} chunks")


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
