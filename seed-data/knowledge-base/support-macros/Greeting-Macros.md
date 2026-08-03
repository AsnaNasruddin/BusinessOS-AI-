# Acme Robotics — Greeting Macros

*Knowledge base: Support Macros*

Canned openings and sign-offs for the support agent to draw on. These are
tone references, not rigid templates — the drafting agent should adapt
wording to the specific situation rather than pasting these verbatim.

## Opening Lines

- **New issue, first contact:** "Hi {{first_name}}, thanks for reaching out —
  sorry to hear about {{brief_issue_summary}}."
- **Damage/defect report:** "Hi {{first_name}}, sorry the unit arrived
  {{damaged/not working as expected}}."
- **Order status question:** "Hi {{first_name}}, happy to check that for
  you."
- **Returning customer, known issue thread:** "Hi {{first_name}}, following
  up on your {{order_number}} — here's where things stand."

Avoid: "We sincerely apologize for any inconvenience this may have caused."
It's long, vague, and doesn't tell the customer anything. One short, direct
apology beats a paragraph of hedging (see the tone guidance in
`company-profile.md`).

## Sign-offs

- Standard: "Let me know if you need anything else — happy to help."
- After confirming a refund/replacement: "You'll get a confirmation email
  once this processes. Let me know if it doesn't show up in a few days."
- After escalating to a human: "I've flagged this for a teammate to take a
  closer look — you'll hear from us shortly."

Always sign off as "Acme Robotics Support," not an individual name, unless a
human agent has taken over the thread.

## Escalation Hand-off Phrasing

When the AI can't resolve something itself (see `Escalation-Scripts.md` for
the full decision criteria), be upfront about it rather than stalling:

> "This one needs a closer look from our team — I've sent it over and
> someone will follow up shortly. Thanks for your patience."

Don't imply a timeline the team hasn't committed to (no "within the hour"
unless that's an actual SLA).

## Related Documents

- `Escalation-Scripts.md` — when to hand off instead of resolving directly
