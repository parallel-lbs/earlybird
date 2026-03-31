"""Orchestrator: classify -> embed -> layout -> regions -> GeoJSON.

Supports two layout modes:
  - ``build_map()``: UMAP-based organic layout with Voronoi territory regions
  - ``build_map_hierarchical()``: deterministic circle-packing (legacy fallback)

Usage:
    python -m earlybird.map.build_map
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from earlybird.config import DATA_DIR, MAP_DIR
from earlybird.models import Item

log = logging.getLogger(__name__)


def load_feed(date: str | None = None) -> list[Item]:
    """Load daily feed items."""
    feed_path = DATA_DIR / "daily-feed.json"
    if not feed_path.exists():
        log.error("no daily-feed.json found")
        return []

    with open(feed_path) as f:
        data = json.load(f)

    return [Item(**entry) for entry in data.get("items", [])]


def load_from_file(source_path: Path) -> list[Item]:
    """Load items from a backfill or other JSON file.

    Supports two formats:
      - A list of Item dicts (backfill format)
      - A dict with an "items" key (daily-feed format)
    """
    if not source_path.exists():
        log.error("source file not found: %s", source_path)
        return []

    with open(source_path) as f:
        data = json.load(f)

    if isinstance(data, list):
        return [Item(**entry) for entry in data]
    elif isinstance(data, dict) and "items" in data:
        return [Item(**entry) for entry in data["items"]]
    else:
        log.error("unrecognised format in %s", source_path)
        return []


def _load_items(date: str, source_path: Path | None) -> list[Item]:
    """Load items from source_path or daily feed."""
    if source_path is not None:
        return load_from_file(source_path)
    return load_feed(date)


def build_map(date: str | None = None, source_path: Path | None = None) -> Path | None:
    """Run the UMAP-based map pipeline with Voronoi territory regions.

    Pipeline: load -> classify -> embed -> UMAP layout -> Voronoi regions
    -> connections -> GeoJSON.

    Args:
        date: date label for output file naming (defaults to today).
        source_path: if provided, load items from this file instead of daily-feed.json.
    """
    from earlybird.map.connections import compute_category_connections
    from earlybird.map.embedder import embed
    from earlybird.map.geojson import to_geojson
    from earlybird.map.layout import hierarchical_layout, umap_layout
    from earlybird.map.regions import generate_regions
    from earlybird.map.taxonomy import classify_all, get_taxonomy

    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    items = _load_items(date, source_path)
    if not items:
        log.warning("no items to map")
        return None

    log.info("building UMAP map for %d items", len(items))

    # 1. Classify items using taxonomy keywords
    taxonomy = get_taxonomy()
    classifications = classify_all(items)

    # 2. Embed items
    embeddings = embed(items, date)

    # 3. UMAP layout for organic positioning
    coords = umap_layout(embeddings)

    # 4. Generate Voronoi territory regions grouped by SOURCE
    sources = [item.source or "unknown" for item in items]
    x_range = float(coords[:, 0].max() - coords[:, 0].min())
    y_range = float(coords[:, 1].max() - coords[:, 1].min())
    pad_x = max(10.0, x_range * 0.15)
    pad_y = max(10.0, y_range * 0.15)
    bounds = (
        float(coords[:, 0].min()) - pad_x,
        float(coords[:, 1].min()) - pad_y,
        float(coords[:, 0].max()) + pad_x,
        float(coords[:, 1].max()) + pad_y,
    )
    regions = generate_regions(coords, sources, bounds)

    # 5. Build a layout dict compatible with the geojson module
    #    - categories (territories) are data SOURCES
    #    - subcategories are topic classifications within each source
    #    - items get UMAP coordinates
    layout = _build_layout_from_coords(coords, classifications, taxonomy, items)

    # 6. Connections between categories
    connections = compute_category_connections(classifications, layout, taxonomy)

    # 7. Build GeoJSON with regions
    geojson = to_geojson(
        items, classifications, layout, taxonomy,
        connections=connections,
        regions=regions,
    )

    out = MAP_DIR / f"map-{date}.geojson"
    out.write_text(json.dumps(geojson, ensure_ascii=False))
    log.info("wrote map -> %s (%d features)", out, len(geojson["features"]))

    # Also write as latest
    latest = MAP_DIR / "latest.geojson"
    latest.write_text(json.dumps(geojson, ensure_ascii=False))

    return out


def build_map_hierarchical(
    date: str | None = None, source_path: Path | None = None,
) -> Path | None:
    """Run the legacy hierarchical circle-packing pipeline (no embeddings).

    Args:
        date: date label for output file naming (defaults to today).
        source_path: if provided, load items from this file instead of daily-feed.json.
    """
    from earlybird.map.connections import compute_category_connections
    from earlybird.map.geojson import to_geojson
    from earlybird.map.layout import hierarchical_layout
    from earlybird.map.taxonomy import classify_all, get_taxonomy

    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    items = _load_items(date, source_path)
    if not items:
        log.warning("no items to map")
        return None

    log.info("building hierarchical map for %d items", len(items))

    taxonomy = get_taxonomy()
    classifications = classify_all(items)

    layout = hierarchical_layout(classifications, taxonomy)
    connections = compute_category_connections(classifications, layout, taxonomy)
    geojson = to_geojson(items, classifications, layout, taxonomy, connections)

    out = MAP_DIR / f"map-{date}.geojson"
    out.write_text(json.dumps(geojson, ensure_ascii=False))
    log.info("wrote map -> %s (%d features)", out, len(geojson["features"]))

    latest = MAP_DIR / "latest.geojson"
    latest.write_text(json.dumps(geojson, ensure_ascii=False))

    return out


def _build_layout_from_coords(
    coords: np.ndarray,
    classifications: list[tuple[str, str]],
    taxonomy: dict,
    items: list[Item] | None = None,
) -> dict:
    """Build a layout dict from UMAP coordinates, grouped by DATA SOURCE.

    Territories (categories in the layout) are data sources (arxiv, hackernews,
    etc.).  Subcategories are topic classifications within each source territory.

    Returns a dict with the same structure as ``hierarchical_layout()`` output:
    ``{"categories": ..., "subcategories": ..., "items": ...}``.
    """
    import math
    from collections import Counter, defaultdict

    # Determine source per item
    sources: list[str] = []
    if items is not None:
        sources = [item.source or "unknown" for item in items]
    else:
        sources = ["unknown"] * len(coords)

    # Group by SOURCE for territory (category-level) layout
    src_counts: Counter[str] = Counter()
    src_coords: dict[str, list[np.ndarray]] = defaultdict(list)

    # Group by (source, topic_category) for subcategory layout
    sub_counts: Counter[tuple[str, str]] = Counter()
    sub_coords: dict[tuple[str, str], list[np.ndarray]] = defaultdict(list)

    for i, (cat, sub) in enumerate(classifications):
        source = sources[i]
        src_counts[source] += 1
        src_coords[source].append(coords[i])
        sub_counts[(source, cat)] += 1
        sub_coords[(source, cat)].append(coords[i])

    # Source territory centroids with repulsion to avoid label overlap
    categories_layout: dict[str, dict] = {}
    centroids: dict[str, np.ndarray] = {}
    for source, pts in src_coords.items():
        centroids[source] = np.mean(pts, axis=0)

    # Push overlapping centroids apart (simple force-directed repulsion)
    src_names = list(centroids.keys())
    min_sep = 50.0
    for _iteration in range(100):
        moved = False
        for i in range(len(src_names)):
            for j in range(i + 1, len(src_names)):
                ci = centroids[src_names[i]]
                cj = centroids[src_names[j]]
                d = np.linalg.norm(ci - cj)
                if d < min_sep and d > 0.01:
                    direction = (ci - cj) / d
                    push = (min_sep - d) * 0.5
                    centroids[src_names[i]] = ci + direction * push
                    centroids[src_names[j]] = cj - direction * push
                    moved = True
        if not moved:
            break

    for source, centroid in centroids.items():
        radius = max(20.0, 10.0 * math.sqrt(src_counts[source]))
        categories_layout[source] = {
            "coordinates": [round(float(centroid[0]), 6), round(float(centroid[1]), 6)],
            "radius": round(radius, 2),
        }

    # Subcategory centroids: topic categories within each source territory
    subcategories_layout: dict[tuple[str, str], dict] = {}
    for (source, topic_cat), pts in sub_coords.items():
        centroid = np.mean(pts, axis=0)
        count = sub_counts[(source, topic_cat)]
        radius = max(10.0, 6.0 * math.sqrt(count))
        subcategories_layout[(source, topic_cat)] = {
            "coordinates": [round(float(centroid[0]), 6), round(float(centroid[1]), 6)],
            "radius": round(radius, 2),
        }

    # Item coordinates
    items_layout: list[dict] = []
    for i in range(len(coords)):
        items_layout.append({
            "coordinates": [round(float(coords[i, 0]), 6), round(float(coords[i, 1]), 6)],
        })

    return {
        "categories": categories_layout,
        "subcategories": subcategories_layout,
        "items": items_layout,
    }


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    build_map()


if __name__ == "__main__":
    main()
