from __future__ import annotations

import time

from earlybird.config import HN_MIN_POINTS
from earlybird.models import Item
from earlybird.sources.base import Source

ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"
HN_QUERY = "AI OR LLM OR ML OR startup OR GPT OR transformer OR model OR agent"


class HackerNewsSource(Source):
    name = "hackernews"

    def _fetch(self) -> list[Item]:
        ts_24h_ago = int(time.time()) - 86400
        resp = self._get(
            ALGOLIA_URL,
            params={
                "query": HN_QUERY,
                "tags": "story",
                "numericFilters": f"points>{HN_MIN_POINTS},created_at_i>{ts_24h_ago}",
                "hitsPerPage": 50,
            },
        )
        data = resp.json()

        items: list[Item] = []
        for hit in data.get("hits", []):
            obj_id = hit.get("objectID", "")
            ext_url = hit.get("url") or ""
            hn_url = f"https://news.ycombinator.com/item?id={obj_id}"

            items.append(
                Item(
                    source="hackernews",
                    title=hit.get("title", ""),
                    url=ext_url or hn_url,
                    hn_points=hit.get("points"),
                    hn_comments=hit.get("num_comments"),
                    published=hit.get("created_at", ""),
                    extra={"hn_url": hn_url},
                )
            )
        return items
