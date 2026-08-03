# Acme Robotics — Chargeback Guidelines

*Knowledge base: Policy & Refunds*

A chargeback happens when a customer disputes a charge directly with their
bank or card issuer instead of (or in addition to) contacting Acme support.
This document covers how support and the AI agent should handle
chargeback-related conversations — it does not cover the finance team's
internal dispute-response process, which is out of scope for the support
knowledge base.

## If a Customer Mentions a Chargeback Before Contacting Support

If a customer says they've already filed a chargeback ("I disputed this with
my bank"), do not process a standard refund in parallel — a refund issued
while a chargeback is open can result in the customer being paid twice, and
Acme has no reliable way to claw that back. Instead:

1. Acknowledge the situation without confirming or denying anything about
   the dispute.
2. Let the customer know Acme will respond to the bank's inquiry directly
   once received.
3. Escalate to a human agent — this scenario should never be auto-resolved
   by the AI, regardless of dollar amount.

## If Support Notices a Chargeback Notification First

Chargeback notifications arrive through the payment processor, not through
the support inbox, so this scenario is rare in the email-triage workflow but
can come up if a customer replies to an existing thread referencing it.
Same rule applies: escalate, don't auto-resolve.

## Preventing Chargebacks

Most disputes Acme sees stem from slow refund communication, not fraud.
Support should proactively confirm refund timing (5–10 business days to the
original payment method) rather than leaving a customer to wonder whether a
refund was actually processed — a well-timed status update is the single
most effective anti-chargeback measure available to the support flow.

## Related Documents

- `Returns-Policy.md` — the underlying refund terms
- `Refund-Exceptions.md` — cases where a refund wouldn't have been approved
  in the first place, relevant context if a dispute references a denied claim
