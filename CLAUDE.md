# kbgen

Self-contained KB generation product. One Docker image serves both a FastAPI
backend and a React SPA on port **8004**. Polls resolved tickets from an
ITSM (GLPI bundled; ServiceNow / Zendesk behind the same adapter interface
later), drafts KB articles via OpenAI `gpt-4.1`, indexes them into pgvector,
and pushes approved drafts back to the ITSM after human-in-the-loop review.

## Deployment shape

```
  docker compose up  →  Postgres (external) + kbgen stack
  ┌─ bundled in compose ─────────────────────────────────┐
  │  kbgen        FastAPI + SPA on :8004                 │
  │  glpi         pre-configured GLPI on :9080           │
  │  glpi-db      MariaDB backing GLPI                   │
  └──────────────────────────────────────────────────────┘
  customer-provided:  Postgres 14+ with pgvector, OpenAI key
```

Two required env vars: `DATABASE_URL` (external Postgres) and
`OPENAI_API_KEY`. Everything else has defaults.

## Architecture

- **Backend**: FastAPI. Routers under `/api/kb/*`, health at `/api/health`,
  SPA served from `/`. See `src/main.py`.
- **UI**: React + Vite + Tailwind + recharts. Lives in `ui/`. Built into
  `src/static/dist/` and mounted via `StaticFiles`.
- **DB**: `kb.*` schema in the external Postgres. Alembic migrations in
  `src/migrations/` run at container start. Uses `pgvector` for embeddings.
- **LLM**: OpenAI `gpt-4.1` for generation (structured output via JSON
  schema) + `text-embedding-3-small` (1536-dim) for retrieval.
- **Scheduler**: APScheduler 60s poll (configurable via `kb.settings` or
  `POLL_INTERVAL_S` env).
- **First-boot seeder**: when `AUTO_SEED_ITSM=true` and the active ITSM is
  empty, seeds 135 healthcare tickets + 4 KB articles so the UI has
  something to show. See `src/bootstrap.py`.

## App Registry (auto-managed — do not edit manually)

- **Backend port**: 8004 (serves BOTH API and UI)
- **Shared venv**: `~/.appregistry/venvs/ai-full`
- **Activate**: `source ~/.appregistry/venvs/ai-full/bin/activate`
- **Start backend**: `./start.sh` (accepts `--port <n>` or `$PORT` / `$BACKEND_PORT` env)

The old separate frontend port (`3002`) and the separate `kb-portal`
starter in dxp (`4600`) are retired. The UI is now bundled into kbgen
itself.

### Rules for Claude Code

- Do NOT create a project-local venv (`python -m venv .venv` etc.). Use the shared venv.
- Install packages: `source ~/.appregistry/venvs/ai-full/bin/activate && pip install <pkg>`.
- UI source is `ui/`. For HMR dev: `cd ui && pnpm dev` (Vite proxies `/api` → `:8004`). For the single-port experience that matches production: `cd ui && pnpm build` then run kbgen.
- Do NOT add `@dxp/*` dependencies to `ui/package.json`. This project is intentionally self-contained.

### 🔒 Dev Port Lock — defaults only, overridable at launch

- **Backend/UI**: `8004` (one port for both).
- Backend MUST accept a port via `--port` and/or env (`PORT` / `BACKEND_PORT`).
- If the default is busy, surface the conflict (`lsof -i :8004`) rather than silently picking a different port.
- In non-dev environments, port comes from env.

### 🔒 DB Schema Ownership

- `kb.*` tables in the external Postgres are owned by kbgen. All DDL goes through Alembic migrations in `src/migrations/`.
- kbgen does not touch `public.*` tables.

<!-- end-app-registry -->
