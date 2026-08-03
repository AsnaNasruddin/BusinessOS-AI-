# Acme Robotics — Refund Exceptions

*Knowledge base: Policy & Refunds*

The standard 30-day refund window (`Returns-Policy.md`) does not apply
uniformly to every order. This document lists the carve-outs support and the
AI agent should check before promising a refund.

## Final Sale — No Exceptions

Exceptions to the standard refund window apply to custom-configured units and
clearance items, which are final sale. Specifically:

- **Custom-configured units** — any X200 Pro ordered with a non-standard
  color, engraving, or the industrial filtration upgrade. These are built to
  order and cannot be restocked.
- **Clearance / open-box items** — marked as such at checkout, sold at a
  discount specifically because they carry no standard refund coverage.
  Damage or defect claims on clearance items still route to warranty
  (`Warranty-Terms.md`), just not to a standard refund.
- **Digital add-ons** — the companion app's premium monitoring subscription
  is non-refundable once a billing cycle has started, though it can be
  cancelled to prevent renewal.

## Partial Exceptions

- **Bundles** — if a customer bought the X200 with an accessory bundle and
  wants to return only the bundle (keeping the robot), the bundle refund is
  prorated based on the bundle discount, not the individual retail prices of
  each item.
- **Gift purchases** — refunds on gifted units go to store credit for the
  recipient by default, not to the original purchaser's payment method,
  unless the purchaser explicitly requests otherwise and can verify the
  order.

## When the AI Agent Should Escalate Instead of Deciding

If an order matches more than one exception category, or the customer
disputes that their unit is "custom-configured" (configuration disputes do
happen — engraving is sometimes added post-purchase by a retail partner, not
Acme direct), escalate to a human agent rather than resolving it
automatically. This is a judgment call the agent's prompt should be
conservative about.

## Related Documents

- `Returns-Policy.md` — standard policy this document carves out from
- `International-Returns.md` — additional exceptions for non-US orders
