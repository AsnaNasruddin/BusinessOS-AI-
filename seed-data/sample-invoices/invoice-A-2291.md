<!--
Matches the pending Approvals-page demo item: "Invoice #A-2291 — $4,820.00
to Meridian Supplies", "exceeds $2,500 auto-approve threshold"
(frontend/src/lib/seed-data.ts, approvals[1]). This is the source document
the Invoice Approval workflow's trigger payload would be built from —
either a forwarded vendor email with this attached, or a direct upload.
-->

**Vendor:** Meridian Supplies
**Invoice #:** A-2291
**Invoice date:** 2026-07-28
**Due date:** 2026-08-27 (Net 30)
**Bill to:** Acme Robotics, Inc. — Accounts Payable

| Description | Qty | Unit price | Total |
|---|---|---|---|
| Injection-molded housing shells, X200 (batch run) | 400 | $9.85 | $3,940.00 |
| Freight & handling | — | — | $610.00 |
| Expedited processing fee | — | — | $270.00 |
| **Total due** | | | **$4,820.00** |

**Notes from vendor:** Expedited due to the production-line request received
2026-07-24. Standard lead time waived for this batch at no additional
line-item cost beyond the listed expedite fee.

**PO reference:** none on file — this invoice does not match an existing
purchase order, which is itself a reason a human should review it rather
than relying on PO-matching auto-approval, independent of the dollar amount.

---

*Per company policy (`company-profile.md`), invoices above $2,500 require
manager approval regardless of vendor history. This one clears that
threshold on the base total alone, before the expedite fee is even
considered.*
