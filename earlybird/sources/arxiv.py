from __future__ import annotations

import time
import xml.etree.ElementTree as ET

from earlybird.models import Item
from earlybird.sources.base import Source

ARXIV_API = "https://export.arxiv.org/api/query"
CATEGORIES = "cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"
MAX_RESULTS = 100


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
