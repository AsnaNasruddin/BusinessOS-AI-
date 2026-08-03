# Implementation Plan Addendum: Natural Language Workflow Generator

Extends *BusinessOS AI — Implementation Plan v1.0*. Read the base plan first — this
document assumes its terminology, data model, and architectural principles and
never contradicts them. See [ADR 0001](adr/0001-natural-language-workflow-generator.md)
for the short version of the decision and trade-offs.

**Design principle, stated once, binding for every section below:**

> Describe what you want. AI builds the workflow. You review it. You can edit it
> visually or through natural language. Then you activate it.

The Natural Language Workflow Generator (from here, **NLWG**) is a planning layer
in front of the existing engine. It never introduces a second workflow
representation, a second execution path, or a way to skip human review.

---

## 0. Update Summary — what changes where

| Base plan section | Change |
|---|---|
| 1. Project Identity | No change. |
| 2. Learning Goals | No change to the list. NLWG is the feature that exercises nearly all twelve at once — see §16.17. |
| 3. Non-Goals | **Add two bullets** — see §0.1. |
| 4. Technology Stack | No new dependencies. Reuses `LLMClient`, Pydantic v2, Celery, `simpleeval`. |
| 5. High-Level Architecture | **Insert** a "Workflow Generation Layer" between the API and the Agent Runtime in the diagram; **add** architectural principle 6 — see §16.2. |
| 6. Data Model | **Add** `WorkflowGenerationRequest` table; **add** two columns to `Workflow` — see §16.4. |
| 7. Module-by-Module Specification | **Insert new Module 4.5** — see §16 in full. |
| 8. API Design | **Add five endpoints** under `/workflows` — see §16.12. |
| 9. Development Phases | **Insert new Phase 7** (NLWG); the old Phase 7 (Polish + docs) **becomes Phase 8** — see §0.2. |
| 10. Folder Structure | **Add** backend and frontend files — see §16.13–16.14. |
| 12. Instructions for Claude Code | **Add rules 13–14** — see §0.3. |
| 13. Definition of Done | **Add** Phase 7–specific criteria — see §0.4. |
| 14. Common Pitfalls to Avoid | **Add four pitfalls specific to this feature** — see §0.5. |
| 15. Success Criteria | **Add criterion 6** — see §0.6. |
| 11. Local Development Setup | No change. |

The rest of this document is the new **Section 16**, referenced throughout the table
above.

### 0.1 Non-Goals — additions

- **No fully autonomous activation.** The NLWG can generate and propose a workflow;
  it cannot save it as `is_active = true` or apply an edit without an explicit user
  confirmation step. This is a hard rule, not a default (see §16.16).
- **No new tool/agent execution capability.** The NLWG can *draft* an Agent config or
  flag a missing Tool; it cannot invent a working integration BusinessOS doesn't
  already have (Module 8's tool registry is the ceiling).

### 0.2 Development Phases — insertion

```
Phase 6 — Memory + observability        (unchanged)
Phase 7 — Natural Language Workflow      4–5 days   NEW
          Generator
Phase 8 — Polish + docs                  2–3 days   (was Phase 7)
```

**Phase 7 ships:** the planner agent + IR schema + compiler + validator; the
clarifying-questions loop; the human-friendly preview; "Open in Workflow Builder"
handoff; NL-based editing with reviewable diffs. Depends on Phases 2–5 being done
(agents, tools/LLM abstraction, KB, workflow engine, conditions, and approvals must
already exist — the planner has nothing real to plan against otherwise).

**Why not Phase 4.5, right after the Workflow Builder ships?** Because a plan that
uses Condition and Approval nodes (which the worked example in this doc does) can't
be meaningfully validated or demoed until Phase 5 exists. Building the generator
before the pieces it generates *references* would mean building it twice.

### 0.3 Instructions for Claude Code — additions

**13. The NLWG never bypasses the graph validator.** Every generated or edited graph
— no exceptions — passes through the same `validate_graph()` function
(`backend/app/workflows/graph.py`) that manually-built graphs pass through before
`PUT /workflows/{id}`. Do not write a second, "trusted because the AI made it" path.

**14. The compiler is deterministic; the planner is not.** Keep the LLM call
(non-deterministic, prompt-engineered, tested with `fake_adapter.py`) and the
IR-to-graph compiler (pure Python, deterministic, unit-testable with plain pytest)
in separate modules. If you find yourself asking the LLM to compute node coordinates
or generate UUIDs, that logic belongs in the compiler, not the prompt.

### 0.4 Definition of Done — Phase 7 additions

- A user can type a description, answer any clarifying questions, and see a
  human-readable preview — no JSON, no node-type names — before anything is saved.
- The generated workflow opens in the existing Workflow Builder and is editable
  exactly like a manually-built one (same `graph` JSON shape, same version counter).
- Submitting a natural-language edit against an existing workflow produces a diff
  the user must confirm; declining leaves the workflow untouched.
- A missing agent/tool/KB reference is surfaced as a named gap in the preview, never
  silently dropped or silently invented.
- At least one eval set (`backend/tests/evals/nlwg_cases.yaml` or similar) checks
  that a fixed set of sample descriptions compile to the expected node-type sequence.

### 0.5 Common Pitfalls to Avoid — additions

- **Asking the LLM for the final graph JSON.** Ask it for the IR (§16.5); compile
  the graph yourself. The failure mode of a malformed IR is a validation error the
  user can react to; the failure mode of malformed graph JSON is a broken canvas.
- **Forgetting to thread required output fields backward.** If a Condition node
  needs `refund_amount`, the upstream Agent's system prompt must be written (or
  rewritten) to actually return that field. See §16.6.
- **Treating "clarifying questions" as optional polish.** Skipping them and letting
  the user "fix it in the builder" defeats the entire purpose for a non-technical
  user — the loop in §16.7 is core, not a nice-to-have.
- **Applying NL edits directly to the live graph.** Always produce a diff object
  first (§16.11); apply only after explicit confirmation, and only by incrementing
  `Workflow.version` the same way a manual edit would.

### 0.6 Success Criteria — addition

**6.** Type a plain-English description of a support process ("when a customer
emails us, read it, check our policies, draft a reply, and if the refund is over
$500 get a manager's approval first"), answer at most one or two clarifying
questions, review a plain-English summary of the result, and land in the visual
Workflow Builder with a graph that runs — indistinguishable, once saved, from one
built by hand.

---

## 16. Natural Language Workflow Generator

### 16.1 Purpose & Design Principle

Two creation paths, one workflow model:

| | Natural Language Creation | Visual Workflow Builder |
|---|---|---|
| Audience | Non-technical business owner | Technical / advanced user |
| Input | Plain English description | Drag-and-drop nodes + edges |
| Output | Same `Workflow.graph` JSON | Same `Workflow.graph` JSON |
| Where changes land | Compiled, validated, then opened in the builder for review | Directly, via the existing canvas |

They are two front doors into the same house. A workflow doesn't know or care which
door was used to build it — `WorkflowRun`, `WorkflowStep`, `ApprovalRequest`, and
`execute_workflow(run_id)` are all unmodified by this addendum.

### 16.2 Architecture

```
User
 │  natural-language request
 ▼
┌─────────────────────────────────────────────┐
│ Workflow Generation Layer (NEW)              │
│  • Planner Agent (LLMClient, tool-using)     │
│  • Clarifying-question loop                  │
│  • IR → Graph compiler (deterministic)       │
│  • Graph validator (SHARED with manual path) │
└─────────────────────────────────────────────┘
 │  validated Workflow.graph JSON
 ▼
Human Review  ──────────────────────────────────┐
 │  (existing) React Flow Workflow Builder       │  same component,
 │                                                │  same props, same
 ▼                                                │  save/activate flow
Existing Workflow Engine (execute_workflow) ◄─────┘
 │
 ▼
Agents + Tools + RAG + Memory + Human Approval
 │
 ▼
Logs + Analytics
```

**Architectural principle 6 (added to Section 5):** *Natural language becomes a
workflow graph through the same validated path as a manual edit.* The Generation
Layer is only ever allowed to *propose* a `Workflow.graph` value. It is never given
write access to `is_active`, and it never calls `execute_workflow` directly.

The Planner Agent is an `Agent` row like any other (Module 5) — it has a
`system_prompt`, a `model_provider`/`model_name`, a `temperature`, and (critically)
an `allowed_tool_ids` list containing three new **read-only** tools (§16.9). It runs
through `AgentExecutor.run()` like every other agent in the system — no bespoke
execution path.

### 16.3 UX Flow → Screens

| Step (from the feature request) | Screen / component | Notes |
|---|---|---|
| 1. Describe the Goal | `DescribeGoalPage` — "What would you like your AI employees to do?" + textarea | Entry point, reachable from the Workflows list ("+ New workflow" → "Describe it" vs "Build it") |
| 2. AI Understands the Request | (no screen — background) | Celery task `generate_workflow_plan`, polled like a `WorkflowRun` |
| 3. Clarifying Questions | `ClarifyingQuestionsPanel` — one question at a time, plain-English | Structured output, not a free chat — see §16.7 |
| 4. Generate the Workflow | (no screen — background) | IR → compiler → validator |
| 5. Human-Friendly Preview | `WorkflowPreviewCard` — numbered plain-English steps, no JSON/DAG/node vocabulary | `[Review Workflow] [Edit] [Activate]` |
| 6. Open in Visual Builder | Existing `WorkflowBuilderPage`, given a `graph` prop | Zero new builder code — it already accepts a graph |
| 7. Natural Language Editing | `NlEditBar` — a single input docked in the Workflow Builder toolbar, next to Save/Run | Produces a diff card (§16.11), not a live edit |

### 16.4 Data Model

Two additions to Section 6, in the same pseudo-schema style.

```
Workflow(
  ... unchanged fields ...
  source (enum: manual|generated|hybrid, default manual),
  generation_request_id (nullable, references WorkflowGenerationRequest)
)
```

`hybrid` is set the first time a `manual` edit is saved against a workflow whose
`source` was `generated` (or vice versa) — a cheap, honest breadcrumb for analytics
("what fraction of generated workflows get hand-edited later?") without needing a
separate audit table.

```
WorkflowGenerationRequest(
  id, org_id, user_id,
  mode (enum: create|edit),
  target_workflow_id (nullable — set when mode = edit),
  raw_text (text),                    -- the user's original description/instruction
  status (enum: pending|awaiting_answers|planning|ready|applied|rejected|failed),
  clarifying_questions (json array, nullable),
  answers (json array, nullable),
  plan (json, nullable),              -- the WorkflowPlan IR, once generated
  diff (json, nullable),              -- populated only when mode = edit, see §16.11
  missing_components (json array, nullable),
  error (text, nullable),
  created_at, updated_at
)
```

One table serves both creation and editing — a `WorkflowGenerationRequest` with
`mode=create` and `target_workflow_id=NULL` behaves like §16.5–16.9; one with
`mode=edit` additionally produces a `diff` (§16.11) instead of a bare `plan`. This
mirrors the base plan's own instinct to reuse one shape rather than fork it
(`WorkflowRun` already serves both manual and scheduled triggers the same way).

### 16.5 Structured Output Schemas

The planner **never emits `Workflow.graph` directly.** It emits a smaller,
easier-to-validate **intermediate representation (IR)** — a flat list of steps and
the edges between them, referencing existing entities by name rather than ID, with
layout and ID-generation left entirely to a deterministic compiler (§16.8). This is
the single most important design decision in this addendum — see the trade-off
discussion in §16.18.

```python
from pydantic import BaseModel
from typing import Literal, Optional

NodeKind = Literal[
    "trigger", "agent", "tool", "condition",
    "approval", "parallel", "merge", "end",
]

class NewAgentDraft(BaseModel):
    """A proposed Agent config the planner wants created — always shown for
    review before any Agent row is written (Module 5 CRUD, not a bypass of it)."""
    name: str
    description: str
    system_prompt: str
    suggested_model: str = "ollama/llama3.1:8b"
    suggested_tools: list[str] = []
    memory_scope: Literal["none", "session", "persistent"] = "none"

class PlanNode(BaseModel):
    ref: str                              # local id, e.g. "n1" — scoped to this plan only
    kind: NodeKind
    label: str                            # human-readable, e.g. "Customer Support Agent"

    trigger_type: Optional[Literal["manual", "webhook", "schedule", "email"]] = None

    agent_ref: Optional[str] = None       # name of an EXISTING Agent, if reused
    new_agent: Optional[NewAgentDraft] = None   # set instead of agent_ref if none fits
    required_output_fields: list[str] = []      # e.g. ["refund_amount"] — see §16.6

    tool_ref: Optional[str] = None        # name of an EXISTING Tool
    kb_ref: Optional[str] = None          # name of a KnowledgeBase, attached to an agent node

    condition_expression: Optional[str] = None    # e.g. "refund_amount > 500"
    condition_description: Optional[str] = None   # "Is the refund over $500?"

    approval_message: Optional[str] = None

class PlanEdge(BaseModel):
    source_ref: str
    target_ref: str
    branch: Optional[Literal["yes", "no"]] = None  # only meaningful when source is a condition

class MissingComponent(BaseModel):
    kind: Literal["agent", "tool", "knowledge_base"]
    name: str
    reason: str   # "This workflow requires access to Gmail, but Gmail has not been connected yet."

class WorkflowPlan(BaseModel):
    summary: str                          # seeds the human-friendly preview (§16.3 step 5)
    nodes: list[PlanNode]
    edges: list[PlanEdge]
    missing_components: list[MissingComponent] = []
    clarifying_questions: list[str] = []  # non-empty ⇒ plan is a draft, not final (§16.7)
```

This is passed as the `response_format` (structured output) to `LLMClient.chat()` —
the same mechanism every other agent in the system uses for JSON-validated output
(Section 2, learning goal 3). No new LLM plumbing.

### 16.6 The Workflow Planner Agent

An ordinary `Agent` row, seeded at install time (like the demo org's other seed
data), with three properties worth calling out:

1. **Read-only tools.** `allowed_tool_ids` includes three new built-in tools
   (Module 8 pattern — `backend/app/tools/builtins/`), each a thin, read-only
   wrapper over an existing `scoped_query()`:
   - `list_agents(org_id)` → `[{name, description, allowed_tools}]`
   - `list_tools()` → `[{name, description, category}]`
   - `list_knowledge_bases(org_id)` → `[{name, description}]`

   This is what lets the planner say *"reuse the existing Draft Reply Writer agent"*
   instead of drafting a duplicate every time — a direct application of Section 2's
   function-calling/tool-use goal, in service of the "reuse existing systems"
   requirement.

2. **Backward field-threading.** When the planner emits a `condition_expression`
   like `refund_amount > 500`, it must also set `required_output_fields =
   ["refund_amount"]` on the upstream agent node whose output the condition reads,
   and that agent's `system_prompt` (existing or `new_agent.system_prompt`) must
   explicitly instruct the model to return that field. The planner's own system
   prompt carries a rule to this effect and the compiler (§16.8) **rejects** a plan
   where a condition references a field no upstream node declares — a cheap,
   mechanical check that catches the single most common failure mode of
   LLM-authored branching logic.

3. **Context engineering.** Per Section 2 goal 2, the planner's context window is
   assembled fresh per turn from: the raw request, prior clarifying answers, and the
   *live* output of the three read-only tools above — never a stale cached list of
   agents/tools. This matters because the whole point of reuse-over-duplication is
   that it reflects what the org actually has today.

### 16.7 Clarifying Questions Loop

A **generate → evaluate → improve** cycle (Section 2, learning goal 7 — loop
engineering), bounded and structured, not an open-ended chat:

1. Planner call #1 returns a `WorkflowPlan`. If `clarifying_questions` is non-empty,
   the plan is necessarily partial — the compiler refuses to compile a plan with
   pending questions.
2. The frontend shows the questions **one at a time** (`ClarifyingQuestionsPanel`),
   each with a short free-text answer field.
3. Each answer is appended to `WorkflowGenerationRequest.answers` and a new planner
   call is made with the full history (original text + all Q&A pairs) in context.
4. Repeat until `clarifying_questions` comes back empty, **capped at 3 rounds** — if
   the planner still has open questions after 3 rounds, it must instead populate
   `missing_components` and produce its best-effort plan, deferring the rest to the
   visual builder. (A generator that interrogates a business owner indefinitely has
   failed at its one job.)

This cap is a deliberate scope boundary: NLWG optimizes for "get to a reviewable
draft fast," not "extract a perfect spec via chat."

### 16.8 Compiler: IR → Graph

`backend/app/services/workflow_generation/compiler.py` — pure, deterministic,
unit-tested with plain pytest fixtures (no LLM, no `fake_adapter.py` needed here at
all, which is precisely the point of separating it from the planner).

```python
def compile_plan_to_graph(plan: WorkflowPlan, org_id: str) -> dict:
    """
    Deterministic. Given a validated WorkflowPlan:
      1. Resolve agent_ref / tool_ref / kb_ref against real DB rows (scoped_query).
      2. Generate a real node id (uuid4) per PlanNode.ref.
      3. Auto-layout: simple layered left-to-right placement, one column per BFS
         depth from the trigger node — same coordinate space the Workflow Builder
         canvas already renders (node width/height constants shared, not redefined).
      4. Emit `{"nodes": [...], "edges": [...]}` in the EXACT shape
         `Workflow.graph` already uses (Section 6) — node shape
         {id, type, position, data}, matching what React Flow and the engine expect.
      5. Raise CompileError (not a silent best-effort) on any unresolvable
         reference or unthreaded required_output_field (§16.6).
    """
```

Because this function is pure and synchronous, it can also be reused, unmodified,
by the diff-apply path in §16.11 — one compiler, two callers.

### 16.9 Validation Pipeline

Before a compiled graph is persisted, it passes the **same** `validate_graph()`
used for manual `PUT /workflows/{id}` edits (Section 12, Rule 13 above), which
already must check, per the base plan's engine requirements:

- No orphan or unreachable nodes; graph terminates in an `end` node.
- Every `condition` node's expression parses under the existing `simpleeval`-based
  evaluator (Section 12, Rule 6) — **parse-checked here, never executed** at
  generation time.
- Every referenced `agent_id`, `tool_id`, and `kb_id` exists and belongs to `org_id`
  (the same `scoped_query()` helper, Section 12 Rule 7).
- `approval` nodes have a non-empty message template.

NLWG adds exactly one check on top, specific to itself: the backward-threading rule
from §16.6 (a condition's referenced fields must appear in some upstream node's
`required_output_fields`). Everything else is inherited, not reimplemented.

### 16.10 Missing Component Detection & Assisted Creation

When the planner can't find a suitable existing Agent, Tool, or KnowledgeBase, it
populates `missing_components` (§16.5) instead of guessing. The preview screen
(§16.3 step 5) surfaces each one as plain language:

> *"This workflow requires access to Gmail, but Gmail has not been connected yet."*
> *"This workflow requires a Customer Support Agent. Would you like me to create one
> using the following configuration?"* → shows the `NewAgentDraft` fields
> (system prompt, model, tools, memory scope) in the same editor UI Module 5
> already has (`AgentEditor` component, reused, not rebuilt).

Creating the drafted Agent is a normal `POST /agents` call the user explicitly
triggers by clicking "Create agent" — the planner drafts, the user decides, the
existing Module 5 endpoint writes. A missing Tool (e.g., an unconnected Gmail
integration) cannot be auto-created — Module 8 tools are code, not config — so it is
always surfaced as a hard gap the plan routes around or pauses on.

### 16.11 Natural Language Editing (diff-based)

`POST /workflows/{id}/edit-with-nl` runs the **same planner agent**, but in `mode:
edit`: the prompt additionally includes the target workflow's current `graph` JSON
(summarized back into IR form, not raw JSON, for the same reasons as §16.5) plus the
instruction text (*"Change the refund approval limit from $500 to $1,000"*). It
returns a **partial** `WorkflowPlan` describing only the changed nodes/edges plus a
`change_summary: str`.

`compute_graph_diff(current_graph, partial_plan) -> WorkflowDiff` produces:

```python
class WorkflowDiff(BaseModel):
    change_summary: str                 # "Refund threshold changed from $500 to $1,000"
    nodes_added: list[dict]
    nodes_removed: list[str]            # node ids
    nodes_modified: list[dict]          # {id, before, after}
    edges_added: list[dict]
    edges_removed: list[str]
```

The frontend renders this as a plain-English change list (never a raw JSON diff) —
`NlEditDiffCard`, shown before anything touches the saved workflow. Confirming calls
`POST /workflows/{id}/edit-with-nl/{request_id}/apply`, which:

1. Re-validates the resulting full graph through the same pipeline as §16.9.
2. Writes it via the **existing** `PUT /workflows/{id}` code path, which already
   increments `Workflow.version` (Section 6) — no parallel versioning logic.
3. Sets `Workflow.source = 'hybrid'` if it wasn't already `manual`.

Declining discards the `WorkflowGenerationRequest` (status → `rejected`); the live
workflow is never touched.

### 16.12 API Design (addition to Section 8)

```
POST   /workflows/generate                     # {mode:"create", description}
GET    /workflows/generate/{request_id}         # poll status — mirrors GET /runs/{id}
POST   /workflows/generate/{request_id}/answer   # {answer} — clarifying-question loop
POST   /workflows/generate/{request_id}/compile  # explicit "generate now" once questions are done
POST   /workflows/{id}/edit-with-nl              # {instruction} → returns request_id + diff
POST   /workflows/edit-with-nl/{request_id}/apply
POST   /workflows/edit-with-nl/{request_id}/reject
```

All return the standard `{ "data": ..., "meta": {...} }` envelope (Section 8). The
generation endpoints enqueue a Celery task and return `202` with the
`WorkflowGenerationRequest.id`, exactly mirroring how `POST /workflows/{id}/run`
enqueues `execute_workflow(run_id)` rather than running synchronously (Section 5,
architectural principle 1 — unchanged, just applied here too).

### 16.13 Backend Service Layout (addition to Section 10)

```
backend/app/
├── api/v1/
│   └── workflow_generation.py
├── services/
│   └── workflow_generation/
│       ├── planner.py          # builds context, calls AgentExecutor.run() for the planner agent
│       ├── schemas.py          # WorkflowPlan, PlanNode, PlanEdge, WorkflowDiff, etc. (§16.5, §16.11)
│       ├── compiler.py         # compile_plan_to_graph() (§16.8) — pure, no LLM
│       ├── diff.py             # compute_graph_diff() (§16.11) — pure, no LLM
│       └── validator_bridge.py # thin wrapper calling the EXISTING workflows/graph.py validator
├── agents/prompts/
│   └── workflow_planner.md     # the planner agent's system prompt template
├── tools/builtins/
│   ├── list_agents.py          # NEW read-only tool (§16.6)
│   ├── list_tools.py           # NEW read-only tool
│   └── list_knowledge_bases.py # NEW read-only tool
└── worker/tasks.py             # + generate_workflow_plan(request_id)
```

### 16.14 Frontend Components (addition to Section 10)

```
frontend/src/features/
└── workflow-generator/
    ├── describe-goal-page.tsx      # Step 1
    ├── clarifying-questions-panel.tsx  # Step 3
    ├── workflow-preview-card.tsx   # Step 5 — plain English, no JSON/DAG vocabulary
    ├── missing-component-card.tsx  # §16.10, reuses AgentEditor from features/agents
    ├── nl-edit-bar.tsx             # Step 7 — docked in the Workflow Builder toolbar
    ├── nl-edit-diff-card.tsx       # §16.11 diff review
    └── use-workflow-generation.ts  # TanStack Query hooks for §16.12, polling like use-runs.ts
```

`use-workflow-generation.ts` follows the exact pattern already established in
`frontend/src/hooks/use-runs.ts` — poll `GET /workflows/generate/{request_id}` on an
interval while `status` is `pending|planning`, matching how a running `WorkflowRun`
is already polled. The Workflow Builder page gains one new prop
(`initialGraph?: WorkflowGraph`) so `describe-goal-page.tsx` → `workflow-preview-card.tsx`
→ "Review Workflow" can hand off into the **existing, unmodified** builder component.

### 16.15 Observability & Evaluation

- Every planner call and every compile/validate step writes a `LogEntry` (Section 6)
  scoped to the `WorkflowGenerationRequest.id` instead of a `run_id` — same table,
  same viewer (Module 11), one more foreign key path.
- Token usage and latency are tracked exactly like any other `AgentExecutor.run()`
  call (Module 5) — no special-casing needed in the cost/analytics rollups (Module
  10) since the planner is a normal `Agent`.
- **Evaluation (Section 2, learning goal 12):** a fixed eval set —
  `backend/tests/evals/nlwg_cases.yaml` — of sample descriptions paired with the
  expected *node-kind sequence* (not exact wording) they should compile to. Run in
  CI against `fake_adapter.py` with canned planner responses for the deterministic
  compiler tests, and manually against a real model before each release to catch
  prompt drift. This is the project's first real eval harness — a good candidate to
  generalize to Agent testing broadly in a later phase.

### 16.16 Security & Safety Rules

Restating and extending Section 12's existing hard rules for this feature
specifically:

1. **Never `eval()`.** Condition expressions from the planner go through the exact
   same restricted evaluator as manually-typed ones (Rule 6) — parsed, not executed,
   at generation time, and only ever executed at run time inside the sandboxed
   evaluator.
2. **Never auto-activate.** `WorkflowGenerationRequest` reaching `status: ready`
   does not touch `Workflow.is_active`. Only an explicit `POST
   /workflows/{id}/run`-equivalent user action, or the existing "Activate" toggle in
   the builder, can.
3. **Every org-scoped read the planner's tools perform uses `scoped_query()`** (Rule
   7) — a planner agent must never be able to list or reference another org's
   agents, tools, or knowledge bases.
4. **Rate-limit generation requests** per org (simple counter, reuse whatever
   throttling the Celery broker config already supports) — a chat-shaped input box
   is the most abuse-prone surface in the product.
5. **The planner's `allowed_tool_ids` is read-only, by construction.** It is never
   granted `send_email`, `http_request`, or any state-changing tool — it plans
   workflows, it does not run them.

### 16.17 Learning Goals Mapping

| # | Goal | Where NLWG exercises it |
|---|---|---|
| 1 | Prompt engineering | The planner's system prompt (§16.6) is the most demanding prompt in the project — reasoning about intent, existing-vs-new components, and backward field-threading at once. |
| 2 | Context engineering | Fresh per-turn context assembly from raw request + Q&A history + live tool results (§16.6). |
| 3 | Structured outputs | `WorkflowPlan`, `MissingComponent`, `WorkflowDiff` — all Pydantic-validated LLM output (§16.5, §16.11). |
| 4 | Function calling / tool use | `list_agents`, `list_tools`, `list_knowledge_bases` — the planner's only tools (§16.6). |
| 5 | RAG | The planner reasons about *when* to attach a KB to an agent node vs. insert an explicit `search_kb` tool node (§16.4 discussion in §16.18). |
| 6 | Memory | N/A directly — the planner is stateless per request by design (§16.7's bounded loop is explicit history in-context, not persistent memory). |
| 7 | Loop engineering | The clarifying-questions cycle, capped and structured (§16.7). |
| 8 | Graph engineering | The whole feature *is* graph engineering at one remove — planning a DAG rather than hand-wiring one (§16.8). |
| 9 | Multi-agent orchestration | The planner agent producing work that other agents (drafted or referenced) will later execute — planning-time orchestration of run-time orchestration. |
| 10 | Human-in-the-loop | The entire UX (§16.3) is built around mandatory review — arguably the feature's core thesis. |
| 11 | Observability | §16.15 — logged like any other agent execution. |
| 12 | Evaluation | §16.15's eval harness — the project's first. |

### 16.18 Architectural Trade-offs

**IR vs. direct graph generation.** Chosen: IR + deterministic compiler (§16.5,
§16.8). Cost: more code, two things to test instead of one. Benefit: the
highest-error-rate part of the problem (coordinates, ID generation, handle wiring)
is removed from the LLM's job entirely, and a bad LLM response fails as a Pydantic
validation error long before it becomes a corrupted graph. Given this is a learning
project where "graph engineering" is an explicit goal (Section 2, #8), building the
compiler by hand is also simply more educational than trusting the model to do
graph mechanics.

**One `WorkflowGenerationRequest` table for both create and edit.** Chosen over two
separate tables. Cost: a few nullable columns that only apply to one mode. Benefit:
one status lifecycle, one polling hook on the frontend, one place to look at "what
has the AI proposed for this org lately" for observability — consistent with the
base plan's general preference for reusing shapes (`WorkflowRun` already serves
manual and scheduled triggers alike).

**Implicit KB-on-agent vs. explicit `search_kb` tool node.** The base plan supports
both (Module 5 mentions agents with a configured KB retrieving automatically; Module
8 lists `search_kb` as an explicit tool). NLWG's planner defaults to **implicit**
(attach `kb_ref` to the agent) for the common case — "check our policies" folded
into one agent step — and only emits an **explicit** tool node when the user's
description implies a distinct, conditionally-skippable lookup (the "if the
category needs a lookup" branching case, as in the base plan's own Customer Support
Triage example). This is a judgment call the planner's system prompt encodes as a
rule of thumb, not a hard constraint — an advanced user can always restructure it in
the visual builder either way.

**Bounded clarifying-question loop (3 rounds) vs. unbounded chat.** Chosen for
predictability and to keep the feature feeling like "describe once, review once"
rather than an open-ended conversation. Cost: a genuinely ambiguous request may
still need visual-builder cleanup after generation. Accepted — the visual builder
existing as a fallback is exactly why this trade-off is safe to make (§16.1's table
— the two paths are meant to meet in the middle).

**Planner tool access is read-only by construction.** Chosen over giving the
planner broader access "to be more capable." A planning agent with write access to
`send_email` or `http_request` is a prompt-injection risk multiplier for no
corresponding benefit — it only ever needs to *describe* a workflow, never *run*
one.
