# Build context: ./frontend (see docker-compose.yml)
# Dev-mode container — runs the Vite dev server, not a production build.
# Node 22+ required — Corepack's pnpm (11.x) needs node:sqlite, added in 22.5+.
FROM node:22-alpine

WORKDIR /app

RUN corepack enable

COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml* ./
RUN pnpm install --frozen-lockfile

COPY . .

EXPOSE 5173

CMD ["pnpm", "dev", "--host", "0.0.0.0"]
