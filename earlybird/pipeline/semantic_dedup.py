"""Fuzzy deduplication via cosine similarity on title embeddings.

Catches rephrased duplicates / reprints that exact dedup misses.
Uses sentence-transformers locally — no API calls.
"""

from __future__ import annotations

import logging

import numpy as np
from sentence_transformers import SentenceTransformer

from earlybird.models import Item

log = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"  # 80MB, fast, good for short texts
SIMILARITY_THRESHOLD = 0.93


def semantic_dedup(items: list[Item], threshold: float = SIMILARITY_THRESHOLD) -> list[Item]:
    """Remove near-duplicate items based on title embedding similarity."""
    if len(items) < 2:
        return items

    log.info("encoding %d titles with %s", len(items), MODEL_NAME)
    model = SentenceTransformer(MODEL_NAME)

    titles = [it.title for it in items]
    embeddings = model.encode(titles, normalize_embeddings=True, show_progress_bar=False)

    # Cosine similarity = dot product (embeddings are L2-normalized)
    sim_matrix = np.dot(embeddings, embeddings.T)

    drop = set()
    for i in range(len(items)):
        if i in drop:
            continue
        for j in range(i + 1, len(items)):
            if j in drop:
                continue
            if sim_matrix[i][j] >= threshold:
                log.debug(
                    "semantic dup (%.3f): %r ↔ %r",
                    sim_matrix[i][j],
                    items[i].title[:60],
                    items[j].title[:60],
                )
                drop.add(j)

    kept = [it for idx, it in enumerate(items) if idx not in drop]
    log.info("semantic dedup: %d → %d (removed %d)", len(items), len(kept), len(drop))
    return kept
