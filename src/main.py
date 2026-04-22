"""kbgen — FastAPI application entrypoint.

Serves two things on one port:
  • /api/*     — REST API (health + kb resources under /api/kb/*)
  • /          — React SPA built into src/static/dist/ by `ui/` (optional:
                 the mount is skipped when the dist dir is missing so dev
                 against the Python service alone still works).
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api import admin, drafts, health, pipeline, search, settings, stats, tickets, topics
from src.bootstrap import schedule_bootstrap
from src.scheduler import start_scheduler, stop_scheduler

STATIC_DIR = Path(__file__).resolve().parent / "static" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # First-boot seeder kicks off in the background so startup isn't blocked
    # by ITSM round-trips. Scheduler runs immediately; it will pick up any
    # newly-seeded tickets on its next tick.
    schedule_bootstrap()
    scheduler = start_scheduler()
    app.state.scheduler = scheduler
    try:
        yield
    finally:
        stop_scheduler(scheduler)


app = FastAPI(title="kbgen", version="0.1.0", lifespan=lifespan)

# CORS still permissive for local dev where Vite may hit /api from :5173.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── REST API ─────────────────────────────────────────────────────────────
# Health lives under /api so a same-origin SPA can always reach it.
app.include_router(health.router, prefix="/api", tags=["health"])

# All kb-specific endpoints go under /api/kb. The routers internally still
# declare paths like /stats, /drafts, /tickets, etc.; the prefix here is
# the only place we name the namespace.
for module, tag in [
    (stats, "stats"),
    (pipeline, "pipeline"),
    (drafts, "drafts"),
    (tickets, "tickets"),
    (topics, "topics"),
    (search, "search"),
    (settings, "settings"),
    (admin, "admin"),
]:
    app.include_router(module.router, prefix="/api/kb", tags=[tag])


# ── Static SPA ───────────────────────────────────────────────────────────
# Serve hashed asset bundles from /assets, then a catch-all route returns
# index.html for any non-API path so client-side routing (/, /workspace,
# /search, /admin, …) works.
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    from fastapi.responses import FileResponse, JSONResponse

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # API paths already matched above; anything arriving here is the SPA.
        # Refuse to serve index.html for paths that LOOK like API calls to
        # surface typos as 404s rather than mysterious HTML in the network tab.
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/")
    async def root():
        return {
            "service": "kbgen",
            "version": "0.1.0",
            "ui": "not built — run `cd ui && pnpm build` to populate src/static/dist",
        }
