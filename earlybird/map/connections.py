"""Compute edges between related categories for the map.

Uses keyword overlap between subcategories to determine which categories
are related, then generates Bezier curves between their layout positions.
"""

from __future__ import annotations

import logging
from collections import defaultdict

import numpy as np

log = logging.getLogger(__name__)


def compute_category_connections(
    classifications: list[tuple[str, str]],
    layout: dict,
    taxonomy: dict,
    min_shared_fraction: float = 0.005,
    max_edges: int = 30,
    curvature: float = 0.2,
) -> list[dict]:
    """Compute edges between categories based on keyword overlap.

    Two categories are connected if their subcategories share keywords.
    The similarity score is the Jaccard index of the combined keyword sets.

    Parameters
    ----------
    classifications:
        ``(category, subcategory)`` per item.
    layout:
        The output of ``hierarchical_layout()``.
    taxonomy:
        The full taxonomy dict.
    min_shared_fraction:
        Minimum Jaccard similarity to draw an edge.
    max_edges:
        Maximum number of edges to return.
    curvature:
        Bezier curve curvature for the connection lines.

    Returns
    -------
    List of connection dicts with coordinates, labels, and similarity.
    """
    cat_layout = layout.get("categories", {})
    active_cats = list(cat_layout.keys())

    if len(active_cats) < 2:
        return []

    # ── Gather keyword sets per category ──────────────────────────────────
    cat_keywords: dict[str, set[str]] = {}
    for cat in active_cats:
        cat_info = taxonomy.get(cat, {})
        subcats = cat_info.get("subcategories", {})
        keywords: set[str] = set()
        for sub_info in subcats.values():
            for kw in sub_info.get("keywords", []):
                keywords.add(kw.lower())
        cat_keywords[cat] = keywords

    # ── Also factor in item co-occurrence ─────────────────────────────────
    # Count items per category
    cat_counts: dict[str, int] = defaultdict(int)
    for cat, _ in classifications:
        cat_counts[cat] += 1

    # ── Compute pairwise Jaccard similarity ───────────────────────────────
    candidates: list[tuple[str, str, float]] = []
    for i, cat_a in enumerate(active_cats):
        kw_a = cat_keywords.get(cat_a, set())
        for cat_b in active_cats[i + 1 :]:
            kw_b = cat_keywords.get(cat_b, set())
            if not kw_a or not kw_b:
                continue
            intersection = kw_a & kw_b
            union = kw_a | kw_b
            jaccard = len(intersection) / len(union) if union else 0.0
            if jaccard >= min_shared_fraction:
                candidates.append((cat_a, cat_b, jaccard))

    # Sort by similarity descending, take top max_edges
    candidates.sort(key=lambda x: x[2], reverse=True)
    candidates = candidates[:max_edges]

    # ── Generate connection lines ─────────────────────────────────────────
    connections: list[dict] = []
    for cat_a, cat_b, sim in candidates:
        p0 = np.array(cat_layout[cat_a]["coordinates"], dtype=float)
        p1 = np.array(cat_layout[cat_b]["coordinates"], dtype=float)
        curve_pts = _bezier_curve(p0, p1, curvature, n_points=20)

        color_a = taxonomy.get(cat_a, {}).get("color", "#999999")
        color_b = taxonomy.get(cat_b, {}).get("color", "#999999")
        blended = _blend_hex_colors(color_a, color_b)

        connections.append({
            "source_category": cat_a,
            "target_category": cat_b,
            "source_label": cat_a,
            "target_label": cat_b,
            "similarity": round(sim, 4),
            "coordinates": curve_pts,
            "color": blended,
        })

    log.info("computed %d inter-category connections", len(connections))
    return connections


def _bezier_curve(
    p0: np.ndarray,
    p1: np.ndarray,
    curvature: float,
    n_points: int = 20,
) -> list[list[float]]:
    """Generate a quadratic Bezier curve between two 2D points.

    The control point is offset perpendicular to the midpoint.
    """
    mid = (p0 + p1) / 2.0
    diff = p1 - p0
    dist = float(np.linalg.norm(diff))

    # Perpendicular direction
    perp = np.array([-diff[1], diff[0]])
    perp_norm = float(np.linalg.norm(perp))
    if perp_norm > 0:
        perp = perp / perp_norm

    control = mid + perp * curvature * dist

    # Sample quadratic Bezier: B(t) = (1-t)^2 * P0 + 2(1-t)t * C + t^2 * P1
    points: list[list[float]] = []
    for i in range(n_points):
        t = i / (n_points - 1)
        pt = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * control + t**2 * p1
        points.append([round(float(pt[0]), 6), round(float(pt[1]), 6)])

    return points


def _blend_hex_colors(hex_a: str, hex_b: str) -> str:
    """Average two hex colors and return as rgba with transparency."""
    try:
        r = (int(hex_a[1:3], 16) + int(hex_b[1:3], 16)) // 2
        g = (int(hex_a[3:5], 16) + int(hex_b[3:5], 16)) // 2
        b = (int(hex_a[5:7], 16) + int(hex_b[5:7], 16)) // 2
        return f"rgba({r},{g},{b},0.3)"
    except (ValueError, IndexError):
        return "rgba(255,255,255,0.3)"
