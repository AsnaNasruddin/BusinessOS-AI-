#!/usr/bin/env python3
"""Seed the dev database with demo data — Acme Robotics (see seed-data/).

Run inside the backend container per the quickstart:
    docker compose exec backend python scripts/seed_dev_data.py

This is a stub until the phases it depends on exist. Each step below is
written now so the shape is right, filled in as its phase ships — don't
jump ahead and implement e.g. create_agents() before Phase 2 lands
(Section 12, rule 2).
"""

import asyncio
import sys
from pathlib import Path

SEED_DATA_DIR = Path(__file__).parent.parent / "seed-data"


async def create_demo_org_and_user() -> None:
    """Phase 1 (Auth + Orgs). Creates the 'Acme Robotics' org and the demo
    user (demo@businessos.ai / demo1234) from seed-data/company-profile.md."""
    print("TODO(phase 1): create demo org + user — see seed-data/company-profile.md")


async def create_demo_agents() -> None:
    """Phase 2 (Tools + LLM abstraction). Creates the four agents already
    described in frontend/src/lib/seed-data.ts (Triage Classifier, Draft
    Reply Writer, Memory Extractor, Lead Enrichment Agent)."""
    print("TODO(phase 2): create demo agents")


async def create_demo_knowledge_bases() -> None:
    """Phase 3 (Knowledge Base / RAG). Walks seed-data/knowledge-base/,
    creates one KnowledgeBase per subfolder, and runs each .md file through
    the REAL ingestion pipeline (app/rag/ingest.py) — not hand-written
    Chunk rows. See seed-data/README.md for the folder-to-KB mapping."""
    if not SEED_DATA_DIR.exists():
        print(f"seed-data/ not found at {SEED_DATA_DIR} — nothing to ingest yet.")
        return
    print("TODO(phase 3): ingest seed-data/knowledge-base/ through the real pipeline")


async def create_demo_workflows() -> None:
    """Phase 4-5 (Workflow engine + approvals). Creates the six workflows
    from frontend/src/lib/seed-data.ts, including the Customer Support
    Triage graph used throughout the design docs."""
    print("TODO(phase 4-5): create demo workflows")


async def main() -> None:
    print("Seeding BusinessOS AI dev data...")
    await create_demo_org_and_user()
    await create_demo_agents()
    await create_demo_knowledge_bases()
    await create_demo_workflows()
    print("Done (see TODOs above for what's not implemented yet).")


if __name__ == "__main__":
    if not (Path(__file__).parent.parent / "backend" / "app").exists():
        print("Run this from the repo root.", file=sys.stderr)
        sys.exit(1)
    asyncio.run(main())
