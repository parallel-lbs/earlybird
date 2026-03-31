from __future__ import annotations

from datetime import datetime, timezone

from earlybird.config import HF_PAPERS_MIN_UPVOTES, HF_TOKEN
from earlybird.models import Item
from earlybird.sources.base import Source

API_URL = "https://huggingface.co/api/daily_papers"


class HFPapersSource(Source):
    name = "hf_papers"

    def _fetch(self) -> list[Item]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self._fetch_for_date(today, min_upvotes=HF_PAPERS_MIN_UPVOTES)

    def fetch_date(self, date: str, min_upvotes: int = 3) -> list[Item]:
        """Fetch papers for a specific date (YYYY-MM-DD), with a lower upvote threshold for historical data."""
        return self._fetch_for_date(date, min_upvotes=min_upvotes)

    def _fetch_for_date(self, date: str, min_upvotes: int = 5) -> list[Item]:
        headers = {}
        if HF_TOKEN:
            headers["Authorization"] = f"Bearer {HF_TOKEN}"

        resp = self._get(API_URL, params={"date": date}, headers=headers)
        data = resp.json()

        items: list[Item] = []
        for entry in data:
            paper = entry.get("paper", {})
            upvotes = entry.get("numUpvotes", 0)
            if upvotes < min_upvotes:
                continue

            arxiv_id = paper.get("id", "")
            items.append(
                Item(
                    id=f"arxiv:{arxiv_id}",
                    source="huggingface_papers",
                    title=paper.get("title", ""),
                    abstract=paper.get("summary", ""),
                    url=f"https://huggingface.co/papers/{arxiv_id}",
                    arxiv_url=f"https://arxiv.org/abs/{arxiv_id}",
                    authors=[a.get("name", "") for a in paper.get("authors", [])],
                    upvotes=upvotes,
                    published=paper.get("publishedAt", ""),
                )
            )
        return items
