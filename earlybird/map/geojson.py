"""Convert hierarchical layout + items to GeoJSON FeatureCollection.

Produces three types of features (distinguished by ``properties.node_type``):
  - **category**: large circle at the category centroid
  - **subcategory**: medium circle at the subcategory centroid
  - **item**: small circle for each individual item
"""

from __future__ import annotations

from earlybird.map.taxonomy import get_category_color, get_source_color
from earlybird.models import Item


def signal_score(item: Item) -> float:
    """Composite signal score normalized to 0..1."""
    score = 0.0
    if item.upvotes:
        score += min(item.upvotes / 50, 1.0) * 0.3
    if item.hn_points:
        score += min(item.hn_points / 500, 1.0) * 0.3
    if item.github_stars:
        score += min(item.github_stars / 200, 1.0) * 0.2
    if item.citation_count:
        score += min(item.citation_count / 100, 1.0) * 0.1
    if item.downloads:
        score += min(item.downloads / 10000, 1.0) * 0.1
    return round(score, 3)


def _subcategory_color(taxonomy: dict, category: str, subcategory: str) -> str:
    """Derive a color for a subcategory.

    Uses the parent category's color with a slight brightness shift based
    on the subcategory's position within the category.
    """
    base = get_category_color(category)
    # Shift brightness slightly per subcategory index
    cat_info = taxonomy.get(category, {})
    subs = list(cat_info.get("subcategories", {}).keys()) if cat_info else []
    if subcategory in subs:
        idx = subs.index(subcategory)
    else:
        idx = 0
    # Lighten or darken by ~10% per index step
    try:
        r = int(base[1:3], 16)
        g = int(base[3:5], 16)
        b = int(base[5:7], 16)
        shift = (idx - len(subs) // 2) * 15
        r = max(0, min(255, r + shift))
        g = max(0, min(255, g + shift))
        b = max(0, min(255, b + shift))
        return f"#{r:02x}{g:02x}{b:02x}"
    except (ValueError, IndexError):
        return base


def to_geojson(
    items: list[Item],
    classifications: list[tuple[str, str]],
    layout: dict,
    taxonomy: dict,
    connections: list[dict] | None = None,
    regions: dict[str, list[list[list[float]]]] | None = None,
) -> dict:
    """Build a GeoJSON FeatureCollection for the hierarchical map.

    Parameters
    ----------
    items:
        The list of ``Item`` objects.
    classifications:
        ``(category, subcategory)`` per item, same order as *items*.
    layout:
        The output of ``hierarchical_layout()``.
    taxonomy:
        The full taxonomy dict.
    connections:
        Optional list of connection dicts from ``compute_category_connections``.
    regions:
        Optional dict mapping category name to list of polygon coordinate
        rings, as produced by ``generate_regions()``.

    Returns
    -------
    A GeoJSON-like dict ready for ``json.dumps``.
    """
    features: list[dict] = []

    # ── 0. Region polygon features (render at the bottom) ────────────────
    # Regions are now keyed by SOURCE (not topic category)
    if regions:
        from collections import Counter
        # Count items per source for region properties
        src_item_counts: Counter[str] = Counter(
            item.source or "unknown" for item in items
        )

        for source_name, rings in regions.items():
            color = get_source_color(source_name)
            count = src_item_counts.get(source_name, 0)

            if len(rings) == 1:
                # Single polygon
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [rings[0]],
                    },
                    "properties": {
                        "node_type": "region",
                        "label": source_name,
                        "color": color,
                        "source_territory": source_name,
                        "item_count": count,
                    },
                }
            else:
                # MultiPolygon for disconnected regions
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "MultiPolygon",
                        "coordinates": [[ring] for ring in rings],
                    },
                    "properties": {
                        "node_type": "region",
                        "label": source_name,
                        "color": color,
                        "source_territory": source_name,
                        "item_count": count,
                    },
                }
            features.append(feature)

    # ── 1. Category features = SOURCE territories (big labels at low zoom) ─
    cat_layout = layout["categories"]
    # Count items per source
    from collections import Counter as _Counter
    _source_counts = _Counter(item.source or "unknown" for item in items)

    for source_name, info in cat_layout.items():
        color = get_source_color(source_name)
        item_count = _source_counts.get(source_name, 0)
        # Count topic subcategories within this source territory
        n_subs = sum(
            1 for (src, _topic) in layout["subcategories"] if src == source_name
        )
        radius = max(20.0, min(40.0, info["radius"]))

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": info["coordinates"],
            },
            "properties": {
                "node_type": "category",
                "label": source_name,
                "color": color,
                "source_color": color,
                "source_territory": source_name,
                "item_count": item_count,
                "subcategory_count": n_subs,
                "radius": round(radius, 1),
            },
        }
        features.append(feature)

    # ── 2. Subcategory features = TOPIC categories within each source ─────
    sub_layout = layout["subcategories"]
    for (source_name, topic_cat), info in sub_layout.items():
        color = get_category_color(topic_cat)  # topic color
        # Count items that belong to this source AND this topic category
        item_count = sum(
            1 for idx, (cat, _sub) in enumerate(classifications)
            if cat == topic_cat and (items[idx].source or "unknown") == source_name
        )
        radius = max(10.0, min(20.0, info["radius"]))

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": info["coordinates"],
            },
            "properties": {
                "node_type": "subcategory",
                "label": topic_cat,
                "parent_category": source_name,
                "source_territory": source_name,
                "color": color,
                "item_count": item_count,
                "radius": round(radius, 1),
            },
        }
        features.append(feature)

    # ── 3. Item features (small circles) ──────────────────────────────────
    items_layout = layout["items"]
    for i, item in enumerate(items):
        cat, sub = classifications[i]
        source = item.source or "unknown"
        score = signal_score(item)
        radius = 4 + score * 12  # 4..16

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": items_layout[i]["coordinates"],
            },
            "properties": {
                "node_type": "item",
                "id": item.id or f"item:{i}",
                "title": item.title,
                "source": source,
                "url": item.url,
                "category": cat,
                "subcategory": sub,
                "source_territory": source,
                "source_color": get_source_color(source),
                "signal_score": score,
                "radius": round(radius, 1),
                "color": get_category_color(cat),  # topic color for dot
                # Signals for tooltip / panel
                "upvotes": item.upvotes,
                "hn_points": item.hn_points,
                "github_stars": item.github_stars,
                "citation_count": item.citation_count,
                "downloads": item.downloads,
                "likes": item.likes,
                "published": item.published,
                "abstract": (item.abstract or item.snippet or item.description or "")[:300],
                "authors": item.authors[:5] if item.authors else [],
            },
        }
        features.append(feature)

    # ── Metadata ──────────────────────────────────────────────────────────
    # Build hierarchy for legend: source -> [topic categories within]
    hierarchy: dict[str, list[str]] = {}
    for source_name in cat_layout:
        topics = [
            topic_cat for (src, topic_cat) in sub_layout if src == source_name
        ]
        hierarchy[source_name] = topics

    metadata: dict = {
        "total_items": len(items),
        "total_categories": len(cat_layout),
        "total_subcategories": len(sub_layout),
        "hierarchy": hierarchy,
    }

    if connections:
        metadata["connections"] = [
            {
                "type": "LineString",
                "coordinates": c["coordinates"],
                "similarity": c["similarity"],
                "source_label": c["source_label"],
                "target_label": c["target_label"],
                "color": c.get("color", "rgba(255,255,255,0.3)"),
            }
            for c in connections
        ]

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": metadata,
    }
