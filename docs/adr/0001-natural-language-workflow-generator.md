# ADR 0001 — Natural Language Workflow Generator

**Status:** Accepted
**Date:** 2026-08-03
**Extends:** Implementation Plan v1.0
**Full spec:** [`docs/implementation-plan-addendum-nl-workflow-generator.md`](../implementation-plan-addendum-nl-workflow-generator.md)

## Context

The Workflow Builder (Module 4) requires understanding nodes, edges, conditions, and
tool wiring — vocabulary a non-technical business owner doesn't have. Without a
lower-friction entry point, BusinessOS is only as accessible as n8n or Zapier, which
undercuts the "AI Operating System for AI employees" pitch (Section 1): the whole
point is that the *business owner* directs the AI employees, not that they learn a
graph editor first.

## Decision

Add a **Natural Language Workflow Generator** as a planning layer that sits in front
of the existing engine, not beside or instead of it:

1. The user describes a process in plain English.
2. An LLM call (routed through the existing `LLMClient`, no new provider) produces a
   **structured intermediate representation (IR)** — not the final graph JSON directly.
3. A deterministic Python **compiler** turns the validated IR into the exact same
   `Workflow.graph` JSON shape (`{nodes, edges}`) the Workflow Builder already reads
   and the engine already executes.
4. The compiled graph runs through the **same validator** manual graphs use.
5. The user always lands on the existing React Flow Workflow Builder to review before
   saving, and nothing activates without an explicit confirm step.
6. Editing an existing workflow by natural language produces a **reviewable diff**,
   never a silent overwrite.

No second workflow representation, no second execution path, no new node types.

## Consequences

**Positive**

- Every learning goal in Section 2 gets exercised by this feature specifically (see
  addendum §16.17) — it's a capstone, not a detour.
- Zero duplicated execution logic: a generated workflow and a hand-built one are
  indistinguishable to `execute_workflow(run_id)` once saved.
- The compiler is the single place that can be unit-tested exhaustively (Section 12,
  Rule 3 — test-first for the engine — applies here too).

**Negative / costs accepted**

- Two-step generation (IR → compile) is more engineering than "ask the LLM for JSON
  and save it." Accepted deliberately — see Alternatives.
- Requires a new Celery task (`generate_workflow_plan`) and polling/async UX on the
  frontend, mirroring `execute_workflow` — extra moving parts for what looks like a
  simple chat box.
- The planner must reason about *existing* agents/tools/KBs it doesn't have in its
  context window by default — it needs read-only tool access to the registries
  (`list_agents`, `list_tools`, `list_knowledge_bases`), which is itself a small
  agent-with-tools system to build and test.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| LLM emits the final `{nodes, edges}` graph JSON directly | Puts coordinate math, ID generation, and handle-wiring inside the prompt — the highest-error-rate part of the problem — where a malformed response silently produces a broken graph instead of a validation error. |
| A separate "AI-generated workflow" table/engine, kept apart from manual workflows | Violates "workflows are data, not code" (Section 5, principle 2) twice over — doubles the execution surface and immediately drifts from the manual builder. |
| Auto-activate high-confidence generations | Violates Section 2's human-in-the-loop goal and Section 15's non-goal boundary; also just risky for a real inbox/refund flow. |
| Free-text edits applied straight to the graph | No diff to review means no human-in-the-loop for *changes*, only for *creation* — inconsistent, and higher blast radius since edits touch live workflows. |

## Scope boundary

This ADR does not change the Workflow Builder's node types, the engine's execution
model, or the Tool/Agent/KB systems. It adds one new planning layer and one new data
model row type. See the addendum for the full section-by-section diff.
