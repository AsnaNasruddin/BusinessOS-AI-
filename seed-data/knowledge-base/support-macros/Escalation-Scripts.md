# Acme Robotics — Escalation Scripts

*Knowledge base: Support Macros*

Guidance for when the AI support agent should stop and hand off to a human,
and what to say when it does. This complements the Triage Classifier's
`needs_kb` / category logic — escalation is a separate decision from "does
this need a knowledge-base lookup."

## Always Escalate, Never Auto-Resolve

- Chargeback or bank dispute mentioned (`Chargeback-Guidelines.md`).
- Refund or replacement value above **$500** (`company-profile.md`) — this
  routes to the Human Review approval node in the workflow, not a support
  escalation per se, but the same principle applies: the AI drafts, a human
  decides.
- Legal language ("lawyer," "lawsuit," "BBB complaint," "FTC").
- Customer explicitly asks for a manager or human.
- Safety concern (e.g., a report of the unit overheating, smoking, or a
  physical injury) — escalate immediately, do not attempt a policy-based
  resolution.

## Escalate When Uncertain

- The order doesn't clearly match a documented exception in
  `Refund-Exceptions.md` and the agent isn't confident which policy applies.
- Conflicting information (customer says "custom configured," account shows
  standard SKU, or vice versa).
- A request spans multiple categories the Triage Classifier wasn't designed
  to combine (e.g., a warranty claim *and* a billing dispute in the same
  email).

## What "Escalate" Means Technically

In the workflow graph, this is not a rejection — it's routing to a
human-review path rather than the auto-send path. The drafting agent should
still produce its best-effort response as a *suggestion* attached to the
escalation, so the human reviewer isn't starting from a blank page. See the
Workflow Builder's Approval node documentation for how this is wired.

## Escalation Message to the Customer

Keep it short (see `Greeting-Macros.md` for the standard phrasing) and never
promise a specific resolution before a human has actually reviewed it —
"someone will follow up" is safe; "you'll get your refund" is not, until
approved.

## Related Documents

- `Greeting-Macros.md` — tone and phrasing for the hand-off message
- `Refund-Exceptions.md` — the specific policy edge cases referenced above
