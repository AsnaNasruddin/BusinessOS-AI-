# BusinessOS AI — Frontend

React 18 + Vite + TypeScript app for BusinessOS AI. See the
[project root README](../README.md) for the overall product and architecture, and
[`../docs/`](../docs/) for the implementation plan and its addenda.

## Status

Every screen is real, working React — Dashboard, Workflow Builder, Agents,
Knowledge Base, Runs, Approvals, Login. There is no backend yet, so every page
currently reads from `src/lib/seed-data.ts` via the TanStack Query hooks in
`src/hooks/`. Each hook has a `TODO(learning)` comment marking the exact line that
becomes a live `api.get(...)` call once the FastAPI backend exists.

## Scripts

```bash
pnpm install       # install dependencies
pnpm dev           # start the dev server on http://localhost:5173
pnpm build         # type-check (tsc -b) and build for production
pnpm preview       # preview the production build locally
pnpm lint          # eslint
pnpm format        # prettier --write
```

## Environment

Copy `.env.example` to `.env` and set `VITE_API_URL` once the backend is running.
Without it, the app falls back to `/api/v1` (same-origin) — irrelevant today since
nothing actually calls the API yet, but wired for when it does.

## Tech stack

React 18 · Vite · TypeScript · Tailwind CSS · shadcn-style hand-authored primitives
(`src/components/ui/`) · React Flow (`@xyflow/react`) for the Workflow Builder canvas
· Zustand for the light/dark theme store · TanStack Query for data fetching ·
react-hook-form + zod for forms · axios · self-hosted IBM Plex Sans/Mono (no font
CDN).

## Structure

```
src/
├── components/
│   ├── ui/          shadcn-style primitives (Button, Card, Badge, Table, Input, Chip)
│   └── layout/       AppShell, TopBar, DockNav, ThemeToggle, icon set
├── features/         one folder per module (dashboard, workflow-builder, agents, ...)
├── hooks/            TanStack Query hooks — currently backed by seed data
├── lib/              api client, auth token helpers, seed data, utils
├── stores/           Zustand stores (theme)
├── types/            shared domain types mirroring the backend data model
├── router.tsx
└── App.tsx
```
