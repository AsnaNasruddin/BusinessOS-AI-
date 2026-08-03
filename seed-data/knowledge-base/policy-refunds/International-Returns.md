<!--
Demo note: in the seeded frontend data (frontend/src/lib/seed-data.ts), this
document is marked status: "failed" — representing a realistic ingestion
failure (e.g. a scanned/image-only PDF the text extractor couldn't parse
cleanly). The content below is the "real" source text a human would eventually
re-upload as a proper text-based PDF to fix the ingestion failure. Keep this
note if you regenerate the file, so the "failed" demo state still makes sense.
-->

# Acme Robotics — International Returns

*Knowledge base: Policy & Refunds*

## Scope

This document covers return and refund handling for orders shipped outside
the United States. Acme currently ships direct-to-consumer to Canada, the
UK, and the EU; retail-partner sales in other regions follow the partner's
own return policy, not this one.

## Return Window

International orders get a **45-day return window** instead of the standard
30 days, to account for longer transit times. All other terms from
`Returns-Policy.md` apply unchanged — full refund for damaged items, no
return shipping for verified damage claims, refunds above $500 require
manager approval.

## Customs & Duties

Acme does not refund customs duties or import taxes paid at delivery — those
are between the customer and their local customs authority. This should be
stated plainly if a customer asks for a duty refund; it is not an Acme
Robotics fee and support has no ability to process it.

## Return Shipping for Non-Damage Returns

Unlike domestic returns, a non-damage international return (customer changed
their mind, wrong size expectation, etc.) requires the customer to cover
return shipping, deducted from the refund total. Damage and warranty claims
are unaffected by this — those remain free return shipping per
`Shipping-Damage-Claims.md`.

## Currency

Refunds are issued in the currency the original charge was made in. Support
should not attempt to manually calculate exchange-rate-adjusted refund
amounts — the payment processor handles this automatically once a refund is
approved.

## Related Documents

- `Returns-Policy.md` — base policy this document extends
- `Refund-Exceptions.md` — exceptions that also apply internationally
