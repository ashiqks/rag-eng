"""FastAPI entrypoint. Mounts the vanilla frontend so the demo runs from a
single origin (no CORS dance for localhost)."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routes import chat, chat_stream, sessions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("streaming_demo")

app = FastAPI(title="Vertex AI Search streaming demo")
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(chat_stream.router)


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "project": settings.project_id,
        "engine": settings.engine_id,
        "location": settings.location,
    }


# Static frontend mount. Resolved relative to this file so working-dir doesn't matter.
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    log.info("mounted frontend from %s", FRONTEND_DIR)
else:
    log.warning("frontend dir not found at %s - API only", FRONTEND_DIR)


@app.on_event("startup")
async def _startup() -> None:
    log.info(
        "ready: project=%s location=%s engine=%s",
        settings.project_id,
        settings.location,
        settings.engine_id,
    )
