"""Leiden community detection on k-NN similarity graph."""

from __future__ import annotations

import logging

import igraph as ig
import leidenalg
import numpy as np

from earlybird.config import KNN_K, KNN_THRESHOLD, LEIDEN_RESOLUTION

log = logging.getLogger(__name__)


def leiden_cluster(embeddings: np.ndarray) -> list[int]:
    """Cluster items using Leiden on a k-NN cosine similarity graph.

    Returns list of cluster IDs (one per item).
    """
    n = embeddings.shape[0]
    if n < 3:
        return list(range(n))

    # Cosine similarity (embeddings are L2-normalized)
    sim = embeddings @ embeddings.T

    # Build k-NN edges
    k = min(KNN_K, n - 1)
    edges = []
    weights = []
    for i in range(n):
        row = sim[i].copy()
        row[i] = -1  # exclude self
        top_k = np.argsort(row)[-k:]
        for j in top_k:
            if row[j] >= KNN_THRESHOLD and i < j:
                edges.append((i, j))
                weights.append(float(row[j]))

    if not edges:
        log.warning("no edges above threshold, all items in one cluster")
        return [0] * n

    graph = ig.Graph(n=n, edges=edges, directed=False)
    graph.es["weight"] = weights

    partition = leidenalg.find_partition(
        graph,
        leidenalg.RBConfigurationVertexPartition,
        weights=weights,
        resolution_parameter=LEIDEN_RESOLUTION,
        seed=42,
    )

    membership = partition.membership
    n_clusters = len(set(membership))
    log.info("leiden: %d items → %d clusters", n, n_clusters)
    return membership
