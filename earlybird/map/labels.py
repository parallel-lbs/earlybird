"""Auto-label clusters using TF-IDF on titles."""

from __future__ import annotations

import logging
from collections import defaultdict

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

from earlybird.config import CLUSTER_COLORS, SUB_CLUSTERS_PER_CLUSTER, SUB_LABEL_MIN_ITEMS
from earlybird.models import Item

log = logging.getLogger(__name__)


def label_clusters(
    items: list[Item],
    membership: list[int],
    top_n_terms: int = 3,
) -> dict[int, str]:
    """Generate a short label for each cluster from top TF-IDF terms."""
    # Group titles by cluster
    cluster_texts: dict[int, list[str]] = defaultdict(list)
    for item, cid in zip(items, membership):
        text = item.title
        if item.abstract:
            text += " " + item.abstract[:200]
        cluster_texts[cid].append(text)

    # Combine all titles per cluster into one document
    cluster_ids = sorted(cluster_texts.keys())
    docs = [" ".join(cluster_texts[cid]) for cid in cluster_ids]

    if not docs:
        return {}

    vectorizer = TfidfVectorizer(
        max_features=500,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
    )
    tfidf_matrix = vectorizer.fit_transform(docs)
    feature_names = vectorizer.get_feature_names_out()

    labels: dict[int, str] = {}
    for idx, cid in enumerate(cluster_ids):
        row = tfidf_matrix[idx].toarray().flatten()
        top_indices = row.argsort()[-top_n_terms:][::-1]
        terms = [feature_names[i] for i in top_indices if row[i] > 0]
        label = " / ".join(terms) if terms else f"Cluster {cid}"
        labels[cid] = label.title()

    log.info("labeled %d clusters", len(labels))
    return labels


def sub_labels(
    items: list[Item],
    membership: list[int],
    embeddings: np.ndarray,
    coords: np.ndarray,
    n_sub: int = SUB_CLUSTERS_PER_CLUSTER,
    top_n_terms: int = 2,
) -> list[dict]:
    """Extract sub-topic labels within each cluster using KMeans + TF-IDF.

    Returns list of dicts with label, coordinates, parent_cluster, and color.
    """
    # Group items by cluster
    cluster_items: dict[int, list[int]] = defaultdict(list)
    for i, cid in enumerate(membership):
        cluster_items[cid].append(i)

    results: list[dict] = []

    for cid, indices in cluster_items.items():
        if len(indices) < SUB_LABEL_MIN_ITEMS:
            continue

        cluster_embeds = embeddings[indices]
        cluster_coords = coords[indices]

        # Run KMeans on cluster embeddings
        k = min(n_sub, len(indices))
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        sub_membership = km.fit_predict(cluster_embeds)

        # Group texts by sub-cluster
        sub_texts: dict[int, list[str]] = defaultdict(list)
        sub_coords_map: dict[int, list[np.ndarray]] = defaultdict(list)
        for local_i, sub_id in enumerate(sub_membership):
            global_i = indices[local_i]
            item = items[global_i]
            text = item.title
            if item.abstract:
                text += " " + item.abstract[:200]
            sub_texts[sub_id].append(text)
            sub_coords_map[sub_id].append(cluster_coords[local_i])

        # TF-IDF across sub-cluster documents
        sub_ids = sorted(sub_texts.keys())
        docs = [" ".join(sub_texts[sid]) for sid in sub_ids]

        if not docs:
            continue

        vectorizer = TfidfVectorizer(
            max_features=300,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
        )
        tfidf_matrix = vectorizer.fit_transform(docs)
        feature_names = vectorizer.get_feature_names_out()

        for idx, sid in enumerate(sub_ids):
            row = tfidf_matrix[idx].toarray().flatten()
            top_indices = row.argsort()[-top_n_terms:][::-1]
            terms = [feature_names[ti] for ti in top_indices if row[ti] > 0]
            label = " / ".join(terms) if terms else f"Sub {sid}"

            centroid = np.array(sub_coords_map[sid]).mean(axis=0)
            color = CLUSTER_COLORS[cid % len(CLUSTER_COLORS)]

            results.append({
                "label": label.title(),
                "coordinates": [float(centroid[0]), float(centroid[1])],
                "parent_cluster": cid,
                "color": color,
            })

    log.info("extracted %d sub-topic labels", len(results))
    return results
