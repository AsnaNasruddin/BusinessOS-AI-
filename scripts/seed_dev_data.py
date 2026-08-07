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
from pathlib import Path

from sqlalchemy import select

from app.config import get_settings
from app.database.models import Approval, User
from app.database.session import async_session_maker
from app.rag.ingest import ingest_document
from app.schemas.agent import AgentCreate
from app.schemas.kb import KnowledgeBaseCreate
from app.schemas.workflow import WorkflowCreate
from app.services import (
    agent_service,
    approval_service,
    auth_service,
    kb_service,
    org_service,
    workflow_service,
)
from app.workflows.executor import execute_workflow, resume_workflow

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


DEMO_WORKFLOW_NAME = "Weekly Report Digest"


async def create_demo_workflows(org_id) -> None:
    """Phase 4 (Workflow engine v0). Creates one real, linear workflow —
    trigger -> agent -> tool -> end — and runs it once so there's real
    WorkflowRun/WorkflowStep data to look at.

    The richer branching example already sketched in
    frontend/src/lib/seed-data.ts (Customer Support Triage — condition node,
    approval node, parallel send+log) isn't seeded here: v0 only executes
    linear chains (app/workflows/graph.py rejects condition/approval/
    parallel/merge nodes until Phase 5 exists). Seeding that graph now would
    create a workflow nobody can actually run yet."""
    async with async_session_maker() as db:
        existing = await workflow_service.list_workflows(db, org_id=org_id)
        if any(w.name == DEMO_WORKFLOW_NAME for w in existing):
            print(f"  workflow '{DEMO_WORKFLOW_NAME}' already exists, skipping")
            return

        agents = await agent_service.list_agents(db, org_id=org_id)
        triage_agent = next((a for a in agents if a.name == "Triage Classifier"), None)
        if triage_agent is None:
            print("  Triage Classifier agent not found — run create_demo_agents() first")
            return

        graph = {
            "nodes": [
                {
                    "id": "t",
                    "type": "trigger",
                    "position": {"x": 0, "y": 0},
                    "data": {"label": "Weekly Kickoff", "sub": "trigger · manual"},
                },
                {
                    "id": "a",
                    "type": "agent",
                    "position": {"x": 220, "y": 0},
                    "data": {
                        "label": "Triage Classifier",
                        "sub": "agent",
                        "agentId": str(triage_agent.id),
                    },
                },
                {
                    "id": "k",
                    "type": "tool",
                    "position": {"x": 440, "y": 0},
                    "data": {"label": "log_activity", "sub": "tool", "toolName": "log_activity"},
                },
                {
                    "id": "e",
                    "type": "end",
                    "position": {"x": 660, "y": 0},
                    "data": {"label": "Done", "sub": "end"},
                },
            ],
            "edges": [
                {"id": "e1", "source": "t", "target": "a"},
                {"id": "e2", "source": "a", "target": "k"},
                {"id": "e3", "source": "k", "target": "e"},
            ],
        }

        workflow = await workflow_service.create_workflow(
            db,
            org_id=org_id,
            data=WorkflowCreate(
                name=DEMO_WORKFLOW_NAME,
                description="A real, linear v0 demo — summarizes the week and logs it.",
                trigger_type="schedule",
                graph=graph,
            ),
        )
        await db.commit()
        print(f"  created workflow '{DEMO_WORKFLOW_NAME}'")

        run = await workflow_service.create_run(
            db, workflow=workflow, trigger_payload={"period": "this week"}
        )
        await db.commit()
        print(f"  triggered run {run.id}")

        try:
            await execute_workflow(run.id, db, get_settings())
            await db.commit()
        except Exception as exc:  # noqa: BLE001 - report and move on, don't abort the whole seed
            print(f"  FAILED to execute demo run: {exc}")
            return

        await db.refresh(run)
        print(f"  run finished — status={run.status!r}, total_tokens={run.total_tokens}")


DEMO_BRANCHING_WORKFLOW_NAME = "Refund Request Router"


async def create_demo_branching_workflow(org_id) -> None:
    """Phase 5 (Branches + approvals). Exercises every Phase 5 node kind in
    one graph: `condition` (refunds over $200 need review, smaller ones
    don't), `approval` (a real pause point), and a `parallel`/`merge` pair
    (notify by email and log the activity at the same time, then join
    before ending). Runs it once, auto-approving the pending Approval the
    same way POST /approvals/{id}/decide would — the point is a real,
    finished run to look at, not a hand-written one."""
    async with async_session_maker() as db:
        existing = await workflow_service.list_workflows(db, org_id=org_id)
        if any(w.name == DEMO_BRANCHING_WORKFLOW_NAME for w in existing):
            print(f"  workflow '{DEMO_BRANCHING_WORKFLOW_NAME}' already exists, skipping")
            return

        agents = await agent_service.list_agents(db, org_id=org_id)
        triage_agent = next((a for a in agents if a.name == "Triage Classifier"), None)
        if triage_agent is None:
            print("  Triage Classifier agent not found — run create_demo_agents() first")
            return

        graph = {
            "nodes": [
                {
                    "id": "t",
                    "type": "trigger",
                    "position": {"x": 0, "y": 40},
                    "data": {"label": "Refund Requested", "sub": "trigger · manual"},
                },
                {
                    "id": "a",
                    "type": "agent",
                    "position": {"x": 200, "y": 40},
                    "data": {
                        "label": "Triage Classifier",
                        "sub": "agent",
                        "agentId": str(triage_agent.id),
                    },
                },
                {
                    "id": "c",
                    "type": "condition",
                    "position": {"x": 420, "y": 40},
                    "data": {
                        "label": "Amount > $200?",
                        "sub": "condition",
                        "field": "trigger.amount",
                        "operator": "gt",
                        "value": 200,
                    },
                },
                {
                    "id": "k_auto",
                    "type": "tool",
                    "position": {"x": 640, "y": 160},
                    "data": {
                        "label": "log_activity",
                        "sub": "tool · auto-approved",
                        "toolName": "log_activity",
                    },
                },
                {
                    "id": "ap",
                    "type": "approval",
                    "position": {"x": 640, "y": -80},
                    "data": {"label": "Manager Review", "sub": "approval · required"},
                },
                {
                    "id": "p",
                    "type": "parallel",
                    "position": {"x": 860, "y": -80},
                    "data": {"label": "Notify", "sub": "parallel · fan-out"},
                },
                {
                    "id": "k_email",
                    "type": "tool",
                    "position": {"x": 1080, "y": -160},
                    "data": {"label": "send_email", "sub": "tool", "toolName": "send_email"},
                },
                {
                    "id": "k_log",
                    "type": "tool",
                    "position": {"x": 1080, "y": 0},
                    "data": {"label": "log_activity", "sub": "tool", "toolName": "log_activity"},
                },
                {
                    "id": "m",
                    "type": "merge",
                    "position": {"x": 1300, "y": -80},
                    "data": {"label": "Join", "sub": "merge"},
                },
                {
                    "id": "e",
                    "type": "end",
                    "position": {"x": 1500, "y": 40},
                    "data": {"label": "Resolved", "sub": "end"},
                },
            ],
            "edges": [
                {"id": "e1", "source": "t", "target": "a"},
                {"id": "e2", "source": "a", "target": "c"},
                {"id": "e3", "source": "c", "target": "ap", "sourceHandle": "yes"},
                {"id": "e4", "source": "c", "target": "k_auto", "sourceHandle": "no"},
                {"id": "e5", "source": "ap", "target": "p"},
                {"id": "e6", "source": "p", "target": "k_email"},
                {"id": "e7", "source": "p", "target": "k_log"},
                {"id": "e8", "source": "k_email", "target": "m"},
                {"id": "e9", "source": "k_log", "target": "m"},
                {"id": "e10", "source": "m", "target": "e"},
                {"id": "e11", "source": "k_auto", "target": "e"},
            ],
        }

        workflow = await workflow_service.create_workflow(
            db,
            org_id=org_id,
            data=WorkflowCreate(
                name=DEMO_BRANCHING_WORKFLOW_NAME,
                description=(
                    "Refunds over $200 need manager approval before notifying the customer and "
                    "logging it; smaller ones auto-log without review."
                ),
                trigger_type="manual",
                graph=graph,
            ),
        )
        await db.commit()
        print(f"  created workflow '{DEMO_BRANCHING_WORKFLOW_NAME}'")

        run = await workflow_service.create_run(
            db,
            workflow=workflow,
            trigger_payload={
                "amount": 420,
                "customer": "Priya Shah",
                "reason": "damaged unit on arrival",
            },
        )
        await db.commit()
        print(f"  triggered run {run.id} (amount=420 -> should hit the approval branch)")

        try:
            await execute_workflow(run.id, db, get_settings())
            await db.commit()
        except Exception as exc:  # noqa: BLE001 - report and move on, don't abort the whole seed
            print(f"  FAILED to execute demo run: {exc}")
            return

        await db.refresh(run)
        print(f"  run paused at: status={run.status!r}")

        if run.status == "awaiting_approval":
            pending = await db.execute(
                select(Approval).where(Approval.run_id == run.id, Approval.status == "pending")
            )
            approval = pending.scalar_one()
            await approval_service.approve_approval(
                db, approval=approval, decided_by="Jordan Avery (seed script)"
            )
            await db.commit()
            print(f"  auto-approved approval {approval.id}, resuming...")

            try:
                await resume_workflow(run.id, approval.node_id, db, get_settings())
                await db.commit()
            except Exception as exc:  # noqa: BLE001
                print(f"  FAILED to resume demo run: {exc}")
                return

            await db.refresh(run)

        print(f"  run finished — status={run.status!r}, total_tokens={run.total_tokens}")


DEMO_MEMORY_WORKFLOW_NAME = "Customer History Assistant"


async def create_demo_memory_workflow(org_id) -> None:
    """Phase 6 (Memory). trigger -> recall_memories -> agent -> remember_fact
    -> end. Runs it twice for the *same* customer with two different
    messages — since each execute_workflow() call starts from a totally
    fresh in-memory `context` dict, the only way run 2's recall_memories
    step can see run 1's message is through the real AgentMemory table.
    That's the actual thing Phase 6 adds that Phases 4/5 couldn't do."""
    async with async_session_maker() as db:
        existing = await workflow_service.list_workflows(db, org_id=org_id)
        if any(w.name == DEMO_MEMORY_WORKFLOW_NAME for w in existing):
            print(f"  workflow '{DEMO_MEMORY_WORKFLOW_NAME}' already exists, skipping")
            return

        agents = await agent_service.list_agents(db, org_id=org_id)
        triage_agent = next((a for a in agents if a.name == "Triage Classifier"), None)
        if triage_agent is None:
            print("  Triage Classifier agent not found — run create_demo_agents() first")
            return

        graph = {
            "nodes": [
                {
                    "id": "t",
                    "type": "trigger",
                    "position": {"x": 0, "y": 0},
                    "data": {"label": "Customer Message", "sub": "trigger · manual"},
                },
                {
                    "id": "k_recall",
                    "type": "tool",
                    "position": {"x": 220, "y": 0},
                    "data": {
                        "label": "recall_memories",
                        "sub": "tool · memory",
                        "toolName": "recall_memories",
                        "subjectField": "trigger.customer",
                    },
                },
                {
                    "id": "a",
                    "type": "agent",
                    "position": {"x": 440, "y": 0},
                    "data": {
                        "label": "Triage Classifier",
                        "sub": "agent",
                        "agentId": str(triage_agent.id),
                    },
                },
                {
                    "id": "k_remember",
                    "type": "tool",
                    "position": {"x": 660, "y": 0},
                    "data": {
                        "label": "remember_fact",
                        "sub": "tool · memory",
                        "toolName": "remember_fact",
                        "subjectField": "trigger.customer",
                        "factField": "trigger.message",
                    },
                },
                {
                    "id": "e",
                    "type": "end",
                    "position": {"x": 880, "y": 0},
                    "data": {"label": "Done", "sub": "end"},
                },
            ],
            "edges": [
                {"id": "e1", "source": "t", "target": "k_recall"},
                {"id": "e2", "source": "k_recall", "target": "a"},
                {"id": "e3", "source": "a", "target": "k_remember"},
                {"id": "e4", "source": "k_remember", "target": "e"},
            ],
        }

        workflow = await workflow_service.create_workflow(
            db,
            org_id=org_id,
            data=WorkflowCreate(
                name=DEMO_MEMORY_WORKFLOW_NAME,
                description=(
                    "Recalls what's known about a customer, then remembers this message for "
                    "next time."
                ),
                trigger_type="manual",
                graph=graph,
            ),
        )
        await db.commit()
        print(f"  created workflow '{DEMO_MEMORY_WORKFLOW_NAME}'")

        run1 = await workflow_service.create_run(
            db,
            workflow=workflow,
            trigger_payload={
                "customer": "Riley Nakamura",
                "message": "Asked whether the Delta-9 model is back in stock.",
            },
        )
        await db.commit()
        try:
            await execute_workflow(run1.id, db, get_settings())
            await db.commit()
        except Exception as exc:  # noqa: BLE001 - report and move on, don't abort the whole seed
            print(f"  FAILED to execute demo run 1: {exc}")
            return
        await db.refresh(run1)
        print(f"  run 1 finished — status={run1.status!r} (nothing to recall yet, first contact)")

        run2 = await workflow_service.create_run(
            db,
            workflow=workflow,
            trigger_payload={
                "customer": "Riley Nakamura",
                "message": "Following up — still interested, when will it ship?",
            },
        )
        await db.commit()
        try:
            await execute_workflow(run2.id, db, get_settings())
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            print(f"  FAILED to execute demo run 2: {exc}")
            return
        await db.refresh(run2)

        steps = await workflow_service.list_run_steps(db, run_id=run2.id)
        recall_step = next((s for s in steps if s.node_id == "k_recall"), None)
        recalled = recall_step.payload if recall_step and recall_step.payload else []
        print(
            f"  run 2 finished — status={run2.status!r}, recalled {len(recalled)} earlier fact(s):"
        )
        for fact in recalled:
            print(f"    - {fact['fact']!r} (from run 1)")


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
    await create_demo_branching_workflow(org_id)
    await create_demo_memory_workflow(org_id)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
