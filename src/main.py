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
from src.config import get_settings
from src.scheduler import start_scheduler, stop_scheduler

STATIC_DIR = Path(__file__).resolve().parent / "static" / "dist"

_settings = get_settings()


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
# NB: we deliberately do NOT set FastAPI(root_path=BASE_PATH). Starlette
# interprets root_path as "requests arrive prefixed, strip before routing",
# which clashes with the standard nginx pattern (`proxy_pass http://x/`)
# that strips the prefix at the proxy layer. Instead we register a
# middleware below that strips the prefix ourselves when it's present —
# that way the same image works whether the proxy strips or not.

# CORS still permissive for local dev where Vite may hit /api from :5173.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Base-path middleware — strips the configured BASE_PATH prefix from incoming
# request URLs so the same image works (a) behind nginx that already strips
# it and (b) direct without a proxy, where the browser is sending the full
# prefixed URL. No-op when BASE_PATH is unset.
_base_prefix = _settings.normalised_base_path
if _base_prefix:
    @app.middleware("http")
    async def strip_base_path(request, call_next):
        path = request.scope.get("path", "")
        if path.startswith(f"{_base_prefix}/") or path == _base_prefix:
            stripped = path[len(_base_prefix):] or "/"
            request.scope["path"] = stripped
            raw = request.scope.get("raw_path")
            if raw:
                request.scope["raw_path"] = stripped.encode()
        return await call_next(request)

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
    # Single mount — the base-path middleware above already strips any
    # configured BASE_PATH prefix, so incoming `/assets/…` always maps here
    # whether the image is running direct or behind a reverse proxy.
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
