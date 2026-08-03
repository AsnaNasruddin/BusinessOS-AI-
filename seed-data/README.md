# Seed Data

Fake company data for Acme Robotics — the fictional business used in every demo,
screenshot, and seed record across this project. Nothing in this folder is or was
ever real company data; the implementation plan doesn't specify actual content
(see the conversation that produced this folder), so it's fabricated here,
consistently, in one place.

**Start with [`company-profile.md`](company-profile.md).** It's the single source
of truth for names, dollar thresholds, product details, and tone — every other file
in this folder (and the seeded data already in `frontend/src/lib/seed-data.ts`)
should stay consistent with it. If you're generating any new fake content for this
project, check there first.

## What's here

```
seed-data/
├── company-profile.md              company facts, policy thresholds, tone guide
├── knowledge-base/
│   ├── policy-refunds/              7 docs — the Policy & Refunds KB
│   ├── support-macros/              2 docs — the Support Macros KB
│   └── product-docs/                2 docs — the Product Docs KB
├── sample-emails/                   4 trigger payloads, one per Triage category
│                                     + one specifically over the $500 approval threshold
└── sample-invoices/                 1 invoice, over the $2,500 AP approval threshold
```

Every document under `knowledge-base/` is written as real, multi-paragraph prose —
not placeholder text — specifically so the RAG ingestion pipeline (Module 6: parse →
chunk → embed → store) has something realistic to chunk once it exists. Cross-refer-
ences between documents ("see `Refund-Exceptions.md`") are intentional — a good
retrieval test should sometimes need to pull from more than one chunk/document to
fully answer a question.

## How this maps to the implementation plan's data model

| This folder | Becomes (Section 6) |
|---|---|
| `company-profile.md` → the org itself | One `Organization` row ("Acme Robotics") |
| Each subfolder under `knowledge-base/` | One `KnowledgeBase` row |
| Each `.md` file inside those subfolders | One `Document` row, ingested via Module 6's pipeline (the `.md` here stands in for whatever the real upload would be — PDF/DOCX/HTML — the *content* is what matters for chunking/embedding, not the literal file format) |
| Each `sample-emails/*.md` | A `trigger_payload` for a `WorkflowRun` against the Customer Support Triage workflow (`{from, subject, body}`, per Module 4's email trigger type) |
| `sample-invoices/invoice-A-2291.md` | The source content behind the pending Invoice Approval item already shown in the Approvals screen |

## Consistency already locked in with the frontend

Some of this content was written to match, verbatim in places, what's already
seeded in `frontend/src/lib/seed-data.ts` — the RAG retrieval snippets shown in the
Knowledge Base screen's debug panel, and the drafted reply text shown in the
Approvals screen, both trace back to sentences in `knowledge-base/policy-refunds/`.
If you edit either side, check the other for drift.

## Once the backend exists

`scripts/seed_dev_data.py` (Section 11) is the eventual consumer of this folder: it
should walk `knowledge-base/`, create the three `KnowledgeBase` rows, and run each
`.md` file through the real Module 6 ingestion pipeline exactly as if a user had
uploaded it — rather than hand-writing fake `Chunk` rows directly. That's the whole
point of writing real prose here instead of one-line stubs: it should survive
contact with the actual chunker and embedder, not just look right in a mock.
