# kbgen — single-container build: React SPA bundled inside the Python service.
#
# Stage 1 builds the SPA with pnpm.
# Stage 2 runs FastAPI on :8004 and serves the SPA from /.
#
# Build context is the kbgen/ directory alone — no cross-repo copies needed.
# ── Stage 1: build the SPA ──────────────────────────────────────────────
FROM node:20-alpine AS ui
WORKDIR /ui
COPY ui/package.json ui/pnpm-lock.yaml* ./
RUN corepack enable && pnpm install --frozen-lockfile || pnpm install
COPY ui/ ./
# Vite outDir defaults to ../src/static/dist which is outside WORKDIR — the
# config resolves it relative to the ui/ source. Redirect to /ui/dist during
# the image build so stage-2 can copy without traversing parent paths.
RUN pnpm exec tsc -b \
 && pnpm exec vite build --outDir /ui/dist --emptyOutDir

# ── Stage 2: Python service ─────────────────────────────────────────────
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    PORT=8004

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

COPY src/        ./src/
COPY alembic.ini ./
# Drop the built SPA into the path the Python process expects.
COPY --from=ui /ui/dist/ ./src/static/dist/

EXPOSE 8004
HEALTHCHECK --interval=15s --timeout=5s --retries=5 --start-period=30s \
  CMD curl -sf "http://localhost:${PORT}/api/health" > /dev/null || exit 1

# Run Alembic against the customer's external Postgres, then serve.
CMD ["sh", "-c", "alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port ${PORT}"]
