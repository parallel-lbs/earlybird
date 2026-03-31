"""Layout functions for the Earlybird map.

Provides two layout strategies:
  - ``umap_layout``: organic UMAP embedding projection for territory maps
  - ``hierarchical_layout``: deterministic circle-packing from taxonomy
"""

from __future__ import annotations

import logging
import math
import random
from collections import Counter

import numpy as np

from earlybird.config import UMAP_MIN_DIST, UMAP_N_NEIGHBORS

log = logging.getLogger(__name__)

# ── UMAP layout bounds ────────────────────────────────────────────────────────
UMAP_LNG_RANGE = (-150.0, 150.0)
UMAP_LAT_RANGE = (-50.0, 60.0)


def umap_layout(embeddings: np.ndarray) -> np.ndarray:
    """Project embeddings to 2D using UMAP, scaled to lng/lat bounds.

    Parameters
    ----------
    embeddings:
        ``(N, D)`` array of item embeddings.

    Returns
    -------
    ``(N, 2)`` array of ``[lng, lat]`` coordinates.
    """
    import umap

    n_samples = embeddings.shape[0]
    n_neighbors = min(UMAP_N_NEIGHBORS, max(2, n_samples - 1))

    log.info(
        "running UMAP on %d items (n_neighbors=%d, min_dist=%.2f)",
        n_samples, n_neighbors, UMAP_MIN_DIST,
    )

    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=n_neighbors,
        min_dist=UMAP_MIN_DIST,
        metric="cosine",
        random_state=42,
    )
    projected = reducer.fit_transform(embeddings)

    # Scale to lng/lat bounds
    coords = np.empty_like(projected)
    for dim, (lo, hi) in enumerate([UMAP_LNG_RANGE, UMAP_LAT_RANGE]):
        col = projected[:, dim]
        col_min, col_max = col.min(), col.max()
        span = col_max - col_min
        if span < 1e-9:
            coords[:, dim] = (lo + hi) / 2.0
        else:
            coords[:, dim] = lo + (col - col_min) / span * (hi - lo)

    log.info("UMAP layout complete: bounds lng=[%.1f, %.1f] lat=[%.1f, %.1f]",
             coords[:, 0].min(), coords[:, 0].max(),
             coords[:, 1].min(), coords[:, 1].max())

    return coords

# Layout constants
CENTER = (0.0, 20.0)         # Center of the whole layout (lng, lat)
CATEGORY_ORBIT_RADIUS = 80.0  # Radius for placing categories in a ring
SUBCATEGORY_ORBIT_RADIUS = 25.0  # Radius for subcategories around their category
ITEM_SCATTER_RADIUS = 8.0    # Radius for scattering items around subcategory

# Bounds clamp
LNG_BOUNDS = (-170.0, 170.0)
LAT_BOUNDS = (-60.0, 70.0)

# Reproducibility
RNG_SEED = 42


def hierarchical_layout(
    classifications: list[tuple[str, str]],
    taxonomy: dict,
) -> dict:
    """Compute a hierarchical circle-packing layout from classifications.

    Parameters
    ----------
    classifications:
        A list of ``(category, subcategory)`` tuples, one per item.
    taxonomy:
        The full taxonomy dict (from ``get_taxonomy()``).

    Returns
    -------
    dict with keys ``"categories"``, ``"subcategories"``, ``"items"``.
    """
    rng = random.Random(RNG_SEED)

    # ── Count items per category and subcategory ───────────────────────────
    cat_counts: Counter[str] = Counter()
    sub_counts: Counter[tuple[str, str]] = Counter()
    for cat, sub in classifications:
        cat_counts[cat] += 1
        sub_counts[(cat, sub)] += 1

    # Use taxonomy ordering for stable angular assignment
    all_categories = list(taxonomy.keys())
    # Only include categories that actually have items
    active_categories = [c for c in all_categories if cat_counts[c] > 0]
    if not active_categories:
        active_categories = list(cat_counts.keys())

    n_cats = len(active_categories)

    # ── Place categories in a circle ──────────────────────────────────────
    categories_layout: dict[str, dict] = {}
    cat_angle_map: dict[str, float] = {}

    for i, cat in enumerate(active_categories):
        angle = 2.0 * math.pi * i / n_cats - math.pi / 2  # start from top
        lng = CENTER[0] + CATEGORY_ORBIT_RADIUS * math.cos(angle)
        lat = CENTER[1] + CATEGORY_ORBIT_RADIUS * math.sin(angle)
        lng = _clamp(lng, *LNG_BOUNDS)
        lat = _clamp(lat, *LAT_BOUNDS)

        radius = max(20.0, 10.0 * math.sqrt(cat_counts[cat]))
        categories_layout[cat] = {
            "coordinates": [lng, lat],
            "radius": round(radius, 2),
        }
        cat_angle_map[cat] = angle

    # ── Place subcategories around their parent category ──────────────────
    subcategories_layout: dict[tuple[str, str], dict] = {}

    for cat in active_categories:
        cat_coords = categories_layout[cat]["coordinates"]
        # Gather active subcategories for this category
        if cat in taxonomy:
            all_subs = list(taxonomy[cat].get("subcategories", {}).keys())
        else:
            all_subs = []
        active_subs = [s for s in all_subs if sub_counts.get((cat, s), 0) > 0]
        # Also include subcategories not in taxonomy but present in data
        for (c, s), _ in sub_counts.items():
            if c == cat and s not in active_subs:
                active_subs.append(s)

        n_subs = len(active_subs)
        if n_subs == 0:
            continue

        # Angular offset so subcategories fan out away from center
        parent_angle = cat_angle_map.get(cat, 0.0)
        for j, sub in enumerate(active_subs):
            if n_subs == 1:
                sub_angle = parent_angle
            else:
                # Spread subcategories in a ~180-degree arc facing away from center
                spread = min(math.pi, math.pi * 0.8)
                sub_angle = parent_angle - spread / 2 + spread * j / (n_subs - 1)

            orbit_r = SUBCATEGORY_ORBIT_RADIUS
            sub_lng = cat_coords[0] + orbit_r * math.cos(sub_angle)
            sub_lat = cat_coords[1] + orbit_r * math.sin(sub_angle)
            sub_lng = _clamp(sub_lng, *LNG_BOUNDS)
            sub_lat = _clamp(sub_lat, *LAT_BOUNDS)

            count = sub_counts.get((cat, sub), 0)
            radius = max(10.0, 6.0 * math.sqrt(count))
            subcategories_layout[(cat, sub)] = {
                "coordinates": [sub_lng, sub_lat],
                "radius": round(radius, 2),
            }

    # ── Place individual items around their subcategory ───────────────────
    # Track how many items placed per subcategory for spiral placement
    sub_item_index: Counter[tuple[str, str]] = Counter()
    items_layout: list[dict] = []

    for cat, sub in classifications:
        key = (cat, sub)
        sub_info = subcategories_layout.get(key)
        if sub_info is None:
            # Fallback: place near category center
            cat_info = categories_layout.get(cat)
            if cat_info is None:
                items_layout.append({"coordinates": [CENTER[0], CENTER[1]]})
                continue
            base = cat_info["coordinates"]
        else:
            base = sub_info["coordinates"]

        idx = sub_item_index[key]
        sub_item_index[key] += 1
        total = sub_counts.get(key, 1)

        # Place items in a sunflower spiral for even distribution
        coords = _sunflower_point(
            base[0], base[1],
            idx, total,
            radius=ITEM_SCATTER_RADIUS,
            rng=rng,
        )
        coords[0] = _clamp(coords[0], *LNG_BOUNDS)
        coords[1] = _clamp(coords[1], *LAT_BOUNDS)
        items_layout.append({"coordinates": coords})

    log.info(
        "hierarchical layout: %d categories, %d subcategories, %d items",
        len(categories_layout),
        len(subcategories_layout),
        len(items_layout),
    )

    return {
        "categories": categories_layout,
        "subcategories": subcategories_layout,
        "items": items_layout,
    }


def _sunflower_point(
    cx: float, cy: float,
    index: int, total: int,
    radius: float,
    rng: random.Random,
) -> list[float]:
    """Place a point using the sunflower (Fibonacci) spiral with slight jitter.

    This distributes points evenly in a disc without clumping.
    """
    if total <= 1:
        jx = rng.gauss(0, radius * 0.1)
        jy = rng.gauss(0, radius * 0.1)
        return [round(cx + jx, 6), round(cy + jy, 6)]

    golden_angle = math.pi * (3.0 - math.sqrt(5.0))  # ~2.3999...
    r = radius * math.sqrt((index + 0.5) / total)
    theta = index * golden_angle

    # Small jitter for natural look
    jitter_r = rng.gauss(0, radius * 0.03)
    jitter_t = rng.gauss(0, 0.1)

    x = cx + (r + jitter_r) * math.cos(theta + jitter_t)
    y = cy + (r + jitter_r) * math.sin(theta + jitter_t)
    return [round(x, 6), round(y, 6)]


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a value to [lo, hi]."""
    return max(lo, min(hi, value))
