from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from earlybird.models import Item
from earlybird.sources.base import Source

ARXIV_API = "https://export.arxiv.org/api/query"
CATEGORIES = "cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"
MAX_RESULTS = 100

log = logging.getLogger(__name__)


class ArxivSource(Source):
    name = "arxiv"

    def _fetch(self) -> list[Item]:
        items: list[Item] = []
        for start in (0, MAX_RESULTS):
            resp = self._get(
                ARXIV_API,
                params={
                    "search_query": CATEGORIES,
                    "start": start,
                    "max_results": MAX_RESULTS,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                },
            )
            items.extend(self._parse(resp.text))
            if start == 0:
                time.sleep(3)  # respect rate limit
        return items

    def fetch_range(
        self,
        start_date: str,
        end_date: str,
        max_total: int = 5000,
    ) -> list[Item]:
        """Fetch ArXiv papers within a date range, chunked by week.

        Args:
            start_date: YYYY-MM-DD format
            end_date: YYYY-MM-DD format
            max_total: stop after collecting this many items
        """
        dt_start = datetime.strptime(start_date, "%Y-%m-%d")
        dt_end = datetime.strptime(end_date, "%Y-%m-%d")

        # Build weekly chunks
        chunks: list[tuple[datetime, datetime]] = []
        cursor = dt_start
        while cursor < dt_end:
            chunk_end = min(cursor + timedelta(days=7), dt_end)
            chunks.append((cursor, chunk_end))
            cursor = chunk_end

        all_items: list[Item] = []
        seen_ids: set[str] = set()

        for chunk_start, chunk_end in chunks:
            if len(all_items) >= max_total:
                break

            ds = chunk_start.strftime('%Y%m%d')
            de = chunk_end.strftime('%Y%m%d')
            # Build the full URL manually to avoid httpx encoding
            # square brackets, which ArXiv requires unencoded.
            query = f"{CATEGORIES}+AND+submittedDate:[{ds}0000+TO+{de}2359]"

            log.info(
                "arxiv backfill: %s to %s",
                chunk_start.strftime("%Y-%m-%d"),
                chunk_end.strftime("%Y-%m-%d"),
            )

            offset = 0
            while len(all_items) < max_total:
                try:
                    url = (
                        f"{ARXIV_API}?search_query={query}"
                        f"&start={offset}&max_results={MAX_RESULTS}"
                        f"&sortBy=submittedDate&sortOrder=descending"
                    )
                    resp = self._get(url)
                except Exception:
                    log.exception("arxiv request failed at offset %d", offset)
                    break

                page_items = self._parse(resp.text)
                if not page_items:
                    break

                for item in page_items:
                    if item.id not in seen_ids:
                        seen_ids.add(item.id)
                        all_items.append(item)

                if len(all_items) % 100 < len(page_items):
                    log.info("arxiv backfill progress: %d items collected", len(all_items))

                offset += MAX_RESULTS
                time.sleep(3)  # respect rate limit

            time.sleep(3)  # pause between weekly chunks

        log.info("arxiv backfill complete: %d items", len(all_items))
        return all_items[:max_total]

    def _parse(self, xml_text: str) -> list[Item]:
        root = ET.fromstring(xml_text)
        items: list[Item] = []
        for entry in root.findall(f"{ATOM_NS}entry"):
            arxiv_id = (entry.findtext(f"{ATOM_NS}id") or "").split("/abs/")[-1]

            authors = [
                el.findtext(f"{ATOM_NS}name") or ""
                for el in entry.findall(f"{ATOM_NS}author")
            ]

            pdf_url = ""
            for link in entry.findall(f"{ATOM_NS}link"):
                if link.get("title") == "pdf":
                    pdf_url = link.get("href", "")

            cat_el = entry.find(f"{ARXIV_NS}primary_category")
            category = cat_el.get("term", "") if cat_el is not None else ""

            items.append(
                Item(
                    id=f"arxiv:{arxiv_id}",
                    source="arxiv",
                    title=(entry.findtext(f"{ATOM_NS}title") or "").strip().replace("\n", " "),
                    abstract=(entry.findtext(f"{ATOM_NS}summary") or "").strip().replace("\n", " "),
                    url=f"https://arxiv.org/abs/{arxiv_id}",
                    pdf_url=pdf_url,
                    authors=authors,
                    category=category,
                    published=entry.findtext(f"{ATOM_NS}published") or "",
                )
            )
        return items
