"""The project's first real eval harness (addendum §16.15) — checks that a
fixed set of sample descriptions compile to the expected workflow *shape*
(the multiset of node kinds, not exact wording or node order — an LLM's
phrasing and node ordering vary run to run even at low temperature).

Skipped by default: needs a real Ollama running and the seeded Acme
Robotics demo org (scripts/seed_dev_data.py), and is slow — one or more
real LLM round-trips per case. Run explicitly before a release:

    RUN_LLM_EVALS=1 pytest tests/evals/test_nlwg_eval.py -v
"""

import os
from collections import Counter
from pathlib import Path

import pytest
import yaml
from sqlalchemy import select

from app.config import get_settings
from app.database.models import Organization
from app.database.session import async_session_maker
from app.workflow_generation.compiler import compile_plan_to_graph
from app.workflow_generation.planner import generate_plan

pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_LLM_EVALS"),
    reason="needs a real Ollama + seeded demo org — run explicitly with RUN_LLM_EVALS=1",
)

CASES_FILE = Path(__file__).parent / "nlwg_cases.yaml"
CASES = yaml.safe_load(CASES_FILE.read_text())


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
async def test_case_compiles_to_expected_shape(case):
    async with async_session_maker() as db:
        result = await db.execute(
            select(Organization).where(Organization.name == "Acme Robotics")
        )
        org = result.scalar_one()

        plan = await generate_plan(
            raw_text=case["description"],
            clarifying_questions=[],
            answers=[],
            org_id=org.id,
            db=db,
            settings=get_settings(),
        )
        assert not plan.clarifying_questions, (
            f"planner asked a question instead of planning: {plan.clarifying_questions}"
        )

        graph = await compile_plan_to_graph(plan, org_id=org.id, db=db)
        actual_kinds = Counter(n["type"] for n in graph["nodes"])
        expected_kinds = Counter(case["expected_node_kinds"])
        assert actual_kinds == expected_kinds, (
            f"expected {expected_kinds}, got {actual_kinds}\n"
            f"plan: {plan.model_dump_json(indent=2)}"
        )
