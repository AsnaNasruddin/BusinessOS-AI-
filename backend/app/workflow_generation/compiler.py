"""§16.8 — pure, deterministic IR-to-graph compilation. No LLM call happens
in this module, which is the entire point of separating it from the
planner (app.workflow_generation.planner): a bad LLM response fails as a
Pydantic validation error on WorkflowPlan long before it gets here, and
everything this module does — resolving names to real rows, generating
node ids, laying out coordinates, parsing a condition expression — is
100% deterministic and unit-testable with plain pytest fixtures, no
fake_adapter.py needed.

Two judgment calls made resolving this against the REAL engine (not the
addendum's original assumptions, written before Phases 4-5 existed):

1. §16.9 describes condition nodes as parsed by a `simpleeval`-based
   evaluator with a free expression string. The real engine
   (app.workflows.nodes.condition_node) instead uses a structured
   {field, operator, value} shape with no expression parser at all — no
   simpleeval dependency exists in this project. `_parse_condition` below
   bridges the two: the planner still writes a natural expression like
   "refund_amount > 500" (more natural for an LLM, and pairs with
   `condition_description` for the preview UI), and this module parses it
   deterministically into the real shape, resolving `refund_amount`
   against whichever upstream node's `required_output_fields` declared it
   — this IS the backward-threading check §16.6/§16.9 call for, just
   implemented against the real node shape instead of the originally
   planned one.

2. §16.18 discusses an "implicit KB-on-agent" pattern as the common-case
   default. That was never actually built — app.workflows.nodes.agent_node
   only ever serializes the full run context into the prompt; it does no
   retrieval of its own. Only the explicit `search_kb` tool node
   (app.workflows.nodes.tool_node) does real RAG. So this compiler only
   ever emits the explicit form: a `kb_ref` is only valid on a `tool` node
   whose `tool_ref` is "search_kb", and is rejected anywhere else rather
   than silently compiling to a no-op.
"""

import re
import uuid
from collections import defaultdict, deque
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.workflow_generation import CompileError, PlanNode, WorkflowPlan
from app.services import agent_service, kb_service
from app.tools.builtins.registry import TOOL_NAMES

_COLUMN_WIDTH = 220
_ROW_HEIGHT = 130

_CONDITION_PATTERN = re.compile(r"^\s*([\w.]+)\s*(>|<|==|=)\s*(.+?)\s*$")
_OPERATOR_MAP = {">": "gt", "<": "lt", "==": "equals", "=": "equals"}


async def compile_plan_to_graph(plan: WorkflowPlan, *, org_id: uuid.UUID, db: AsyncSession) -> dict:
    errors: list[str] = []

    if plan.clarifying_questions:
        raise CompileError(["Plan still has open clarifying questions — cannot compile yet."])
    if not plan.nodes:
        raise CompileError(["Plan has no nodes."])

    refs = [n.ref for n in plan.nodes]
    if len(set(refs)) != len(refs):
        raise CompileError(["Plan has duplicate node refs."])

    ref_to_id = {n.ref: str(uuid.uuid4()) for n in plan.nodes}
    node_by_ref = {n.ref: n for n in plan.nodes}

    existing_agents = {a.name: a for a in await agent_service.list_agents(db, org_id=org_id)}
    existing_kbs = {kb.name: kb for kb, _count in await kb_service.list_kbs(db, org_id=org_id)}

    compiled_nodes = []
    for node in plan.nodes:
        data, node_errors = _compile_node_data(
            node, node_by_ref, ref_to_id, existing_agents, existing_kbs
        )
        errors.extend(node_errors)
        compiled_nodes.append(
            {
                "id": ref_to_id[node.ref],
                "type": node.kind,
                "position": {"x": 0, "y": 0},
                "data": data,
            }
        )

    edge_errors, compiled_edges = _compile_edges(plan, ref_to_id)
    errors.extend(edge_errors)

    if errors:
        raise CompileError(errors)

    positions = _layout(plan, ref_to_id)
    for compiled, node in zip(compiled_nodes, plan.nodes, strict=True):
        compiled["position"] = positions[node.ref]

    return {"nodes": compiled_nodes, "edges": compiled_edges}


def _compile_node_data(
    node: PlanNode,
    node_by_ref: dict[str, PlanNode],
    ref_to_id: dict[str, str],
    existing_agents: dict[str, Any],
    existing_kbs: dict[str, Any],
) -> tuple[dict, list[str]]:
    errors: list[str] = []
    data: dict = {"label": node.label}

    if node.kind == "trigger":
        data["sub"] = f"trigger · {node.trigger_type or 'manual'}"

    elif node.kind == "agent":
        data["sub"] = "agent"
        agent_name = node.agent_ref or (node.new_agent.name if node.new_agent else None)
        if not agent_name:
            errors.append(f"Node {node.ref!r} (agent) has neither agent_ref nor new_agent.")
        else:
            agent = existing_agents.get(agent_name)
            if agent is None:
                errors.append(
                    f"Node {node.ref!r} references agent {agent_name!r}, which doesn't exist yet "
                    "— create it first (see missing_components), then recompile."
                )
            else:
                data["agentId"] = str(agent.id)
        if node.kb_ref:
            errors.append(
                f"Node {node.ref!r}: attaching a knowledge base directly to an agent isn't "
                "supported — add an explicit search_kb tool node instead."
            )

    elif node.kind == "tool":
        if not node.tool_ref or node.tool_ref not in TOOL_NAMES:
            errors.append(f"Node {node.ref!r} references unknown tool {node.tool_ref!r}.")
        else:
            data["toolName"] = node.tool_ref
            data["sub"] = f"tool · {node.tool_ref}"
            if node.tool_ref == "search_kb":
                if not node.kb_ref:
                    errors.append(f"search_kb node {node.ref!r} needs a kb_ref.")
                elif node.kb_ref not in existing_kbs:
                    errors.append(
                        f"Node {node.ref!r} references knowledge base {node.kb_ref!r}, which "
                        "doesn't exist."
                    )
                else:
                    data["kbId"] = str(existing_kbs[node.kb_ref].id)
                    # The IR has no separate query field (a gap in the original
                    # spec) — the node's own label is the closest natural-
                    # language stand-in, and the planner's system prompt is
                    # written to make that label a genuine search query
                    # ("Search refund policy for damaged items"), not just a
                    # display name.
                    data["query"] = node.label

    elif node.kind == "condition":
        if not node.condition_expression:
            errors.append(f"Condition node {node.ref!r} has no condition_expression.")
        else:
            try:
                field, operator, value = _parse_condition(
                    node.condition_expression, list(node_by_ref.values()), ref_to_id
                )
                data["field"] = field
                data["operator"] = operator
                data["value"] = value
            except CompileError as exc:
                errors.extend(exc.errors)
        data["sub"] = node.condition_description or "condition"

    elif node.kind == "approval":
        data["sub"] = "approval · required"

    elif node.kind == "parallel":
        data["sub"] = "parallel · fan-out"

    elif node.kind == "merge":
        data["sub"] = "merge"

    elif node.kind == "end":
        data["sub"] = "end"

    return data, errors


def _parse_condition(
    expression: str, all_nodes: list[PlanNode], ref_to_id: dict[str, str]
) -> tuple[str, str, Any]:
    match = _CONDITION_PATTERN.match(expression)
    if match:
        field_name, raw_operator, raw_value = match.groups()
        operator = _OPERATOR_MAP[raw_operator]
        value: Any = _coerce_value(raw_value)
    else:
        field_name = expression.strip()
        operator = "truthy"
        value = None

    owner_ref = next((n.ref for n in all_nodes if field_name in n.required_output_fields), None)
    if owner_ref is None:
        raise CompileError(
            [
                f"Condition {expression!r} references field {field_name!r}, but no upstream node "
                f"declares it in required_output_fields — an agent's output must be threaded "
                "backward before a condition can read it."
            ]
        )

    return f"{ref_to_id[owner_ref]}.{field_name}", operator, value


def _coerce_value(raw: str) -> Any:
    raw = raw.strip().strip("\"'")
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _compile_edges(plan: WorkflowPlan, ref_to_id: dict[str, str]) -> tuple[list[str], list[dict]]:
    errors: list[str] = []
    compiled = []
    for i, edge in enumerate(plan.edges):
        if edge.source_ref not in ref_to_id:
            errors.append(f"Edge {i} references unknown source ref {edge.source_ref!r}.")
            continue
        if edge.target_ref not in ref_to_id:
            errors.append(f"Edge {i} references unknown target ref {edge.target_ref!r}.")
            continue
        compiled_edge = {
            "id": f"e{i + 1}",
            "source": ref_to_id[edge.source_ref],
            "target": ref_to_id[edge.target_ref],
        }
        if edge.branch:
            compiled_edge["sourceHandle"] = edge.branch
        compiled.append(compiled_edge)
    return errors, compiled


def _layout(plan: WorkflowPlan, ref_to_id: dict[str, str]) -> dict[str, dict[str, float]]:
    """Simple layered left-to-right placement, one column per BFS depth
    from the trigger node — same coordinate space the Workflow Builder
    canvas already renders."""
    outgoing: dict[str, list[str]] = defaultdict(list)
    for edge in plan.edges:
        outgoing[edge.source_ref].append(edge.target_ref)

    trigger = next((n.ref for n in plan.nodes if n.kind == "trigger"), plan.nodes[0].ref)
    depth = {trigger: 0}
    queue: deque[str] = deque([trigger])
    while queue:
        current = queue.popleft()
        for nxt in outgoing[current]:
            if nxt not in depth:
                depth[nxt] = depth[current] + 1
                queue.append(nxt)
    for node in plan.nodes:
        depth.setdefault(node.ref, 0)

    column_counts: dict[int, int] = defaultdict(int)
    positions = {}
    for node in plan.nodes:
        d = depth[node.ref]
        row = column_counts[d]
        column_counts[d] += 1
        positions[node.ref] = {"x": d * _COLUMN_WIDTH, "y": row * _ROW_HEIGHT}
    return positions
