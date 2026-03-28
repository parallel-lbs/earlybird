from __future__ import annotations

from earlybird.models import Item
from earlybird.sources.base import Source

API_URL = "https://paperswithcode.com/api/v1/papers/"


class PapersWithCodeSource(Source):
    name = "pwc"

    def _fetch(self) -> list[Item]:
        resp = self._get(
            API_URL,
            params={"ordering": "-github_stars", "items_per_page": 50},
        )
        data = resp.json()

        items: list[Item] = []
        for p in data.get("results", []):
            arxiv_url = p.get("url_abs", "")
            arxiv_id = arxiv_url.split("/abs/")[-1] if "/abs/" in arxiv_url else ""

            items.append(
                Item(
                    id=f"arxiv:{arxiv_id}" if arxiv_id else "",
                    source="papers_with_code",
                    title=p.get("title", ""),
                    abstract=p.get("abstract", ""),
                    url=arxiv_url or f"https://paperswithcode.com/paper/{p.get('id', '')}",
                    pdf_url=p.get("url_pdf", ""),
                    github_url=p.get("github_link") or "",
                    github_stars=p.get("stars"),
                    authors=p.get("authors", []),
                    published=p.get("published", ""),
                )
            )
        return items
