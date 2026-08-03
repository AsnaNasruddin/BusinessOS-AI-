# Company Profile — Acme Robotics

Single source of truth for the fictional company behind every demo, seed record,
and screenshot in this project. If you're generating any new fake data — a workflow,
an email, an agent prompt — check here first so it stays consistent with everything
already written.

## Overview

- **Name:** Acme Robotics, Inc.
- **Founded:** 2018
- **HQ:** Austin, Texas
- **Size:** ~140 employees
- **Industry:** Consumer home robotics hardware
- **Sales channels:** Direct-to-consumer online store + select retail partners
  (regional electronics chains, not big-box)

## Product line

- **Model X200** ("the X200") — flagship product, **$399 MSRP**. A home
  companion robot that combines light home-security monitoring (camera +
  patrol) with autonomous floor cleaning. Sold as a single SKU with optional
  accessory bundles (charging dock, extra filters, wall-mounted sensors,
  **$45–$80**).
- **Model X200 Pro** — **$649 MSRP**, same hardware, extended battery + commercial-grade
  filtration, sold to small offices and clinics. Referenced occasionally in
  support content but not a focus of current demo data.
- Older/discontinued: Model X100 (2019–2021) — still shows up in old support
  tickets and warranty edge cases; useful if you need a "this product is no
  longer supported" scenario.

## Support & policy facts (used throughout workflow examples)

These numbers are referenced by name in the workflow builder demo, the runs
timeline, and the approvals queue — keep any new content consistent with them
unless you're deliberately telling a different story.

| Policy | Value |
|---|---|
| Standard return/refund window | 30 days from delivery |
| Refund auto-approval limit (AI can send without a human) | **$500** |
| Refund above $500 | Requires manager approval (Human Review node) |
| Damage claims | No return shipping required for verified damage, must be filed within the 30-day window with photos |
| Custom-configured units / clearance items | Final sale — excluded from standard refund window |
| Accounts Payable auto-approval limit | **$2,500** — invoices above this require manager approval |
| Support hours | Mon–Fri, 8am–6pm CT (email triage workflow runs 24/7; approvals queue during business hours) |

## Org structure (for agent "requested by" / "decided by" fields)

- **Jordan Avery** — Owner / Head of Ops. The default demo user
  (`demo@businessos.ai`). Approves refunds and invoices in demo data.
- **Sam Rivera** — recurring fictional *customer* persona used in support-email
  examples (not an Acme employee).
- **Meridian Supplies** — a recurring fictional *vendor* used in invoice/AP
  examples.

## Voice & tone (for agent system prompts)

Warm, direct, no corporate hedging. Acme's support voice apologizes once,
states the resolution plainly, and never buries the answer in the second
paragraph. Avoid "We sincerely apologize for any inconvenience this may have
caused" — prefer "Sorry the unit arrived damaged."

## Knowledge base map

| Knowledge base | Contents | Path |
|---|---|---|
| Policy & Refunds | Returns, warranty, refund exceptions, shipping damage, chargebacks | `knowledge-base/policy-refunds/` |
| Support Macros | Canned openings, escalation scripts | `knowledge-base/support-macros/` |
| Product Docs | X200 manual, FAQ | `knowledge-base/product-docs/` |

See [`../README.md`](../README.md) (this folder's own README) for how these
files map onto the `Organization` / `KnowledgeBase` / `Document` / `Chunk`
tables from the implementation plan once the backend ingestion pipeline
(Module 6) exists.
