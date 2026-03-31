"""Map API router — endpoints for the interactive map."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from earlybird.auth import verify_token
from earlybird.config import BACKFILL_DIR, MAP_DIR

log = logging.getLogger(__name__)

map_router = APIRouter(tags=["map"])

# ── Backfill state (in-process) ────────────────────────────────────────────
_backfill_status: dict[str, object] = {"running": False, "error": None}


class BackfillRequest(BaseModel):
    days: int = Field(default=365, ge=1, le=730)
    sources: list[str] = Field(default=["arxiv", "hf_papers"])


@map_router.post("/build", dependencies=[Depends(verify_token)])
def build_map_endpoint():
    from earlybird.map.build_map import build_map

    path = build_map()
    if path is None:
        raise HTTPException(500, "map build failed — no items")
    return {"status": "ok", "path": str(path)}


@map_router.get("/geojson")
def get_geojson(date: str | None = Query(None)):
    if date:
        path = MAP_DIR / f"map-{date}.geojson"
    else:
        path = MAP_DIR / "latest.geojson"

    if not path.exists():
        raise HTTPException(404, "no map data — run /map/build first")

    return json.loads(path.read_text())


@map_router.get("/clusters")
def get_clusters():
    path = MAP_DIR / "latest.geojson"
    if not path.exists():
        raise HTTPException(404, "no map data")

    data = json.loads(path.read_text())
    return data.get("metadata", {}).get("cluster_centroids", [])


@map_router.get("/search")
def search_map(q: str = Query(..., min_length=1)):
    path = MAP_DIR / "latest.geojson"
    if not path.exists():
        raise HTTPException(404, "no map data")

    data = json.loads(path.read_text())
    q_lower = q.lower()
    results = []
    for f in data.get("features", []):
        props = f["properties"]
        text = f"{props.get('title', '')} {props.get('abstract', '')}".lower()
        if q_lower in text:
            results.append({
                "id": props["id"],
                "title": props["title"],
                "coordinates": f["geometry"]["coordinates"],
                "signal_score": props["signal_score"],
                "cluster_label": props["cluster_label"],
            })
    return results[:20]


# ── Backfill endpoints ─────────────────────────────────────────────────────

def _run_backfill_task(days: int, sources: list[str]) -> None:
    """Background task: run backfill then build map from the result."""
    global _backfill_status
    try:
        _backfill_status = {"running": True, "error": None}

        from earlybird.backfill import run_backfill
        from earlybird.map.build_map import build_map

        backfill_path = run_backfill(days=days, sources=sources)
        build_map(date="backfill", source_path=backfill_path)

        _backfill_status = {"running": False, "error": None}
        log.info("backfill background task completed successfully")
    except Exception as exc:
        log.exception("backfill background task failed")
        _backfill_status = {"running": False, "error": str(exc)}


@map_router.post("/backfill", dependencies=[Depends(verify_token)])
def backfill_endpoint(req: BackfillRequest, background_tasks: BackgroundTasks):
    if _backfill_status.get("running"):
        raise HTTPException(409, "backfill is already running")

    background_tasks.add_task(_run_backfill_task, req.days, req.sources)
    return {
        "status": "started",
        "days": req.days,
        "sources": req.sources,
        "message": "Backfill started in background. Check /map/backfill/status for progress.",
    }


@map_router.get("/backfill/status")
def backfill_status():
    backfill_file = BACKFILL_DIR / "backfill.json"
    file_info = None
    if backfill_file.exists():
        stat = backfill_file.stat()
        # Count items without loading the full file into memory
        try:
            data = json.loads(backfill_file.read_text())
            item_count = len(data) if isinstance(data, list) else len(data.get("items", []))
        except Exception:
            item_count = None
        file_info = {
            "path": str(backfill_file),
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "item_count": item_count,
        }

    return {
        "running": _backfill_status.get("running", False),
        "error": _backfill_status.get("error"),
        "backfill_file": file_info,
    }
