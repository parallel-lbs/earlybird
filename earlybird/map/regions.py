"""Generate territory polygons from UMAP coordinates using Voronoi tessellation.

Produces a political-map style output where the entire bounding box is covered
by category territories with no gaps — like Map of GitHub.
"""

from __future__ import annotations

import logging
import math

import numpy as np
from scipy.spatial import Voronoi
from shapely.geometry import MultiPolygon, Polygon, box
from shapely.ops import unary_union
from shapely.validation import make_valid

log = logging.getLogger(__name__)


def _polygon_coords(poly: Polygon) -> list[list[float]]:
    """Extract the exterior ring of a Polygon as a list of [lng, lat] pairs."""
    return [[round(x, 4), round(y, 4)] for x, y in poly.exterior.coords]


def _circle_polygon(cx: float, cy: float, radius: float, n: int = 32) -> Polygon:
    """Create a circular polygon approximation for single-point categories."""
    angles = np.linspace(0, 2 * math.pi, n, endpoint=False)
    coords = [(cx + radius * math.cos(a), cy + radius * math.sin(a)) for a in angles]
    coords.append(coords[0])  # close the ring
    return Polygon(coords)


def _extract_polygons(geom) -> list[Polygon]:
    """Extract individual Polygons from any geometry type."""
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    # GeometryCollection or other
    result = []
    if hasattr(geom, "geoms"):
        for g in geom.geoms:
            result.extend(_extract_polygons(g))
    return result


def generate_regions(
    coords: np.ndarray,
    categories: list[str],
    bounds: tuple[float, float, float, float],
    buffer_size: float = 8.0,
    simplify_tolerance: float = 3.0,
) -> dict[str, list[list[list[float]]]]:
    """Generate Voronoi-based territory polygons grouped by category.

    Covers the entire bounding box with no gaps — every pixel belongs to
    a category territory, like a political map.

    Parameters
    ----------
    coords:
        N x 2 array of UMAP-projected [lng, lat] coordinates.
    categories:
        Category label per item, same length as *coords*.
    bounds:
        ``(min_lng, min_lat, max_lng, max_lat)`` bounding box.
    buffer_size:
        Smoothing buffer size. Larger values produce rounder borders.
    simplify_tolerance:
        Polygon simplification tolerance.

    Returns
    -------
    Dict mapping category name to list of polygon coordinate rings.
    """
    if len(coords) == 0 or len(categories) == 0:
        return {}

    coords = np.asarray(coords, dtype=np.float64)
    min_lng, min_lat, max_lng, max_lat = bounds
    bounding_box = box(min_lng, min_lat, max_lng, max_lat)

    # ── Identify unique categories and group point indices ────────────────
    cat_indices: dict[str, list[int]] = {}
    for i, cat in enumerate(categories):
        cat_indices.setdefault(cat, []).append(i)

    # Skip categories with too few items — they create noise fragments
    min_items_for_region = max(10, len(coords) // 100)  # at least 1% of total
    cat_indices = {
        cat: indices for cat, indices in cat_indices.items()
        if len(indices) >= min_items_for_region
    }

    # ── Handle trivial case: single point total ──────────────────────────
    if len(coords) < 2:
        cat = categories[0]
        poly = bounding_box
        return {cat: [_polygon_coords(poly)]}

    # ── Add sentinel points for bounded Voronoi ──────────────────────────
    margin = max(max_lng - min_lng, max_lat - min_lat) * 2.0
    sentinel_points = np.array([
        [min_lng - margin, min_lat - margin],
        [max_lng + margin, min_lat - margin],
        [min_lng - margin, max_lat + margin],
        [max_lng + margin, max_lat + margin],
    ])
    all_points = np.vstack([coords, sentinel_points])

    # ── Compute Voronoi tessellation ─────────────────────────────────────
    try:
        vor = Voronoi(all_points)
    except Exception:
        log.warning("Voronoi computation failed; falling back to circle regions")
        return _fallback_circles(coords, categories, bounds, buffer_size)

    n_real = len(coords)

    # ── Extract clipped Voronoi cells for real points ────────────────────
    point_cells: list[Polygon | None] = [None] * n_real

    for point_idx in range(n_real):
        region_idx = vor.point_region[point_idx]
        region_vertices = vor.regions[region_idx]

        if -1 in region_vertices or len(region_vertices) == 0:
            point_cells[point_idx] = None
            continue

        verts = vor.vertices[region_vertices]
        try:
            cell = Polygon(verts)
            if not cell.is_valid:
                cell = make_valid(cell)
            cell = cell.intersection(bounding_box)
            if cell.is_empty:
                point_cells[point_idx] = None
            else:
                polys = _extract_polygons(cell)
                if polys:
                    point_cells[point_idx] = max(polys, key=lambda p: p.area)
                else:
                    point_cells[point_idx] = None
        except Exception:
            point_cells[point_idx] = None

    # ── Group cells by category and merge (raw, no smoothing yet) ────────
    raw_regions: dict[str, Polygon | MultiPolygon] = {}

    for cat, indices in cat_indices.items():
        cells = [point_cells[i] for i in indices if point_cells[i] is not None]

        if not cells:
            # Fallback circles
            for i in indices:
                c = coords[i]
                circle = _circle_polygon(c[0], c[1], buffer_size * 2)
                circle = circle.intersection(bounding_box)
                if not circle.is_empty:
                    cells.extend(_extract_polygons(circle))
            if not cells:
                continue

        try:
            merged = unary_union(cells)
            if not merged.is_valid:
                merged = make_valid(merged)
            raw_regions[cat] = merged
        except Exception:
            log.warning("unary_union failed for category %s", cat)

    # ── Smooth borders: buffer out → buffer back ─────────────────────────
    # This creates organic-looking borders but may create gaps between
    # territories. We'll fill those gaps in the next step.
    smoothed_regions: dict[str, Polygon | MultiPolygon] = {}

    for cat, geom in raw_regions.items():
        try:
            smooth = geom.buffer(buffer_size).buffer(-buffer_size * 0.5)
            if not smooth.is_valid:
                smooth = make_valid(smooth)
            smooth = smooth.intersection(bounding_box)
            if not smooth.is_empty:
                smoothed_regions[cat] = smooth
        except Exception:
            smoothed_regions[cat] = geom.intersection(bounding_box)

    # ── Fill gaps: assign unclaimed space to nearest category ─────────────
    # This ensures full coverage like a political map.
    all_covered = None
    for geom in smoothed_regions.values():
        if all_covered is None:
            all_covered = geom
        else:
            try:
                all_covered = all_covered.union(geom)
            except Exception:
                pass

    if all_covered is not None:
        try:
            unclaimed = bounding_box.difference(all_covered)
            if not unclaimed.is_empty and unclaimed.area > 0.1:
                # Split unclaimed space into pieces and assign each to nearest category
                unclaimed_polys = _extract_polygons(unclaimed)
                for upoly in unclaimed_polys:
                    if upoly.is_empty or upoly.area < 0.01:
                        continue
                    centroid = upoly.centroid
                    best_cat = None
                    best_dist = float("inf")
                    for cat, geom in smoothed_regions.items():
                        try:
                            dist = geom.distance(centroid)
                            if dist < best_dist:
                                best_dist = dist
                                best_cat = cat
                        except Exception:
                            pass
                    if best_cat:
                        try:
                            expanded = smoothed_regions[best_cat].union(upoly)
                            if not expanded.is_valid:
                                expanded = make_valid(expanded)
                            smoothed_regions[best_cat] = expanded
                        except Exception:
                            pass
        except Exception:
            log.warning("gap-filling step failed; some gaps may remain")

    # ── Simplify and convert to coordinate rings ─────────────────────────
    result: dict[str, list[list[list[float]]]] = {}

    for cat, geom in smoothed_regions.items():
        # Clip to bounding box one final time
        geom = geom.intersection(bounding_box)
        if geom.is_empty:
            continue

        geom = geom.simplify(simplify_tolerance, preserve_topology=True)

        polygons = _extract_polygons(geom)
        # Filter tiny fragments — keep only polygons > 1% of total cat area
        total_area = sum(p.area for p in polygons if not p.is_empty)
        min_area = max(10.0, total_area * 0.05)
        rings: list[list[list[float]]] = []
        for poly in polygons:
            if poly.is_empty or poly.area < min_area:
                continue
            rings.append(_polygon_coords(poly))

        if rings:
            result[cat] = rings

    log.info(
        "generated %d region categories from %d points",
        len(result),
        n_real,
    )
    return result


def _fallback_circles(
    coords: np.ndarray,
    categories: list[str],
    bounds: tuple[float, float, float, float],
    radius: float,
) -> dict[str, list[list[list[float]]]]:
    """Fallback: create circle polygons when Voronoi fails."""
    bounding_box = box(*bounds)
    cat_indices: dict[str, list[int]] = {}
    for i, cat in enumerate(categories):
        cat_indices.setdefault(cat, []).append(i)

    result: dict[str, list[list[list[float]]]] = {}
    for cat, indices in cat_indices.items():
        circles = []
        for i in indices:
            c = _circle_polygon(coords[i, 0], coords[i, 1], radius * 2)
            c = c.intersection(bounding_box)
            if not c.is_empty:
                circles.extend(_extract_polygons(c))
        if circles:
            try:
                merged = unary_union(circles)
                polygons = _extract_polygons(merged)
                rings = [_polygon_coords(p) for p in polygons if not p.is_empty]
                if rings:
                    result[cat] = rings
            except Exception:
                pass

    return result
