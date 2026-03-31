"""Earlybird HTTP API.

Usage:
    python -m earlybird.api                    # default port 41938
    python -m earlybird.api --port 41938       # explicit port
    EARLYBIRD_API_TOKEN=secret python -m earlybird.api  # with auth
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from earlybird.auth import verify_token
from earlybird.config import DATA_DIR

app = FastAPI(title="Earlybird", version="0.2.0")

# CORS for local development and frontend served from different origin
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount map router and static frontend
from earlybird.map_api import map_router
app.include_router(map_router, prefix="/map")

# Mount admin router
from earlybird.admin_api import admin_router
app.include_router(admin_router)

from fastapi.staticfiles import StaticFiles
_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if _frontend_dir.exists():
    # Admin static files must be mounted BEFORE /app so FastAPI matches them first
    _admin_dir = _frontend_dir / "admin"
    if _admin_dir.exists():
        app.mount("/admin", StaticFiles(directory=str(_admin_dir), html=True), name="admin-frontend")
    app.mount("/app", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("earlybird.api")

# ── Models ───────────────────────────────────────────────────────────────────


class ScrapeRequest(BaseModel):
    sources: list[str]


class BuildRequest(BaseModel):
    enrich: bool = False


class StatusResponse(BaseModel):
    status: str
    scraped_at: str | None = None
    total_raw: int | None = None
    total_after_dedup: int | None = None
    total_after_filter: int | None = None
    heartbeat: list[str] | None = None


# ── Endpoints ────────────────────────────────────────────────────────────────


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/scrape", dependencies=[Depends(verify_token)])
def scrape(req: ScrapeRequest):
    from earlybird.scraper import _resolve_sources, _save, scrape as do_scrape

    source_names = _resolve_sources(req.sources)
    if not source_names:
        raise HTTPException(400, f"no valid sources in {req.sources}")

    log.info("scraping: %s", ", ".join(source_names))
    items = do_scrape(source_names)
    tag = "_".join(req.sources)
    path = _save(items, tag)
    return {
        "status": "ok",
        "sources": source_names,
        "items_count": len(items),
        "file": str(path),
    }


@app.post("/build", dependencies=[Depends(verify_token)])
def build_feed(req: BuildRequest):
    from earlybird.build_daily_feed import build

    feed = build()

    if req.enrich:
        from earlybird.sources.semantic_scholar import SemanticScholarEnricher

        enricher = SemanticScholarEnricher()
        try:
            enricher.enrich(feed.items)
        finally:
            enricher.close()

    out = DATA_DIR / "daily-feed.json"
    out.write_text(
        feed.model_dump_json(indent=2, exclude_none=True, exclude_defaults=True),
    )
    return {
        "status": "ok",
        "total_raw": feed.total_raw,
        "total_after_dedup": feed.total_after_dedup,
        "total_after_filter": feed.total_after_filter,
    }


@app.get("/feed", dependencies=[Depends(verify_token)])
def get_feed(limit: int = 50):
    feed_path = DATA_DIR / "daily-feed.json"
    if not feed_path.exists():
        raise HTTPException(404, "no feed yet — run /build first")
    feed = json.loads(feed_path.read_text())
    feed["items"] = feed.get("items", [])[:limit]
    return feed


@app.get("/feed/{item_id:path}", dependencies=[Depends(verify_token)])
def get_feed_item(item_id: str):
    feed_path = DATA_DIR / "daily-feed.json"
    if not feed_path.exists():
        raise HTTPException(404, "no feed yet")
    feed = json.loads(feed_path.read_text())
    for item in feed.get("items", []):
        if item.get("id") == item_id:
            return item
    raise HTTPException(404, f"item {item_id} not found")


@app.get("/status", dependencies=[Depends(verify_token)])
def status():
    feed_path = DATA_DIR / "daily-feed.json"
    heartbeat_path = DATA_DIR / "heartbeat.log"

    resp = StatusResponse(status="ok")

    if feed_path.exists():
        feed = json.loads(feed_path.read_text())
        resp.scraped_at = feed.get("scraped_at")
        resp.total_raw = feed.get("total_raw")
        resp.total_after_dedup = feed.get("total_after_dedup")
        resp.total_after_filter = feed.get("total_after_filter")

    if heartbeat_path.exists():
        lines = heartbeat_path.read_text().strip().splitlines()
        resp.heartbeat = lines[-10:]

    return resp


# ── Entrypoint ───────────────────────────────────────────────────────────────


def main():
    import uvicorn

    parser = argparse.ArgumentParser(description="Earlybird API")
    parser.add_argument("--port", type=int, default=41938)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
