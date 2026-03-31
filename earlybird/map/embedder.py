"""Compute and cache embeddings for feed items."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import numpy as np
from sentence_transformers import SentenceTransformer

from earlybird.config import EMBEDDING_MODEL, EMBEDDINGS_DIR
from earlybird.models import Item

log = logging.getLogger(__name__)


def _text(item: Item) -> str:
    """Combine title + abstract/snippet for richer embedding."""
    parts = [item.title]
    if item.abstract:
        parts.append(item.abstract[:500])
    elif item.snippet:
        parts.append(item.snippet[:500])
    elif item.description:
        parts.append(item.description[:500])
    return " ".join(parts)


def embed(items: list[Item], date: str | None = None) -> np.ndarray:
    """Return (N, D) normalized embeddings. Caches to disk."""
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    cache_path = EMBEDDINGS_DIR / f"{date}.npz"
    if cache_path.exists():
        data = np.load(cache_path)
        cached = data["embeddings"]
        if cached.shape[0] == len(items):
            log.info("loaded cached embeddings from %s", cache_path)
            return cached

    log.info("encoding %d items with %s", len(items), EMBEDDING_MODEL)
    model = SentenceTransformer(EMBEDDING_MODEL)
    texts = [_text(it) for it in items]
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    embeddings = np.array(embeddings, dtype=np.float32)

    np.savez_compressed(cache_path, embeddings=embeddings)
    log.info("cached embeddings → %s", cache_path)
    return embeddings
