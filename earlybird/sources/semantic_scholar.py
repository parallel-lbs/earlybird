from __future__ import annotations

import logging
import time

from earlybird.config import SEMANTIC_SCHOLAR_KEY
from earlybird.models import Item
from earlybird.sources.base import Source

API_URL = "https://api.semanticscholar.org/graph/v1/paper"
BATCH_SIZE = 500
FIELDS = "citationCount,influentialCitationCount,title"

log = logging.getLogger(__name__)


class SemanticScholarEnricher(Source):
    """Not a scrape source — enriches existing items with citation counts."""

    name = "semantic_scholar"

    def _fetch(self) -> list[Item]:
        return []  # not used as a standalone source

    def enrich(self, items: list[Item]) -> list[Item]:
        arxiv_items = [it for it in items if it.id.startswith("arxiv:")]
        if not arxiv_items:
            return items

        id_to_item = {it.id: it for it in arxiv_items}
        arxiv_ids = [f"ArXiv:{it.id.removeprefix('arxiv:')}" for it in arxiv_items]

        headers = {}
        if SEMANTIC_SCHOLAR_KEY:
            headers["x-api-key"] = SEMANTIC_SCHOLAR_KEY

        for i in range(0, len(arxiv_ids), BATCH_SIZE):
            batch = arxiv_ids[i : i + BATCH_SIZE]
            try:
                resp = self.client.post(
                    f"{API_URL}/batch",
                    json={"ids": batch},
                    params={"fields": FIELDS},
                    headers=headers,
                )
                resp.raise_for_status()
                for paper in resp.json():
                    if paper is None:
                        continue
                    ext_id = paper.get("externalIds", {})
                    aid = ext_id.get("ArXiv", "") if ext_id else ""
                    key = f"arxiv:{aid}"
                    if key in id_to_item:
                        id_to_item[key].citation_count = paper.get("citationCount")
            except Exception:
                log.exception("semantic scholar batch enrichment failed")

            if i + BATCH_SIZE < len(arxiv_ids):
                time.sleep(1)

        return items
