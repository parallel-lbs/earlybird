from __future__ import annotations

from earlybird.config import HF_TOKEN
from earlybird.models import Item
from earlybird.sources.base import Source

MODELS_URL = "https://huggingface.co/api/models"
SPACES_URL = "https://huggingface.co/api/spaces"


class HFTrendingModelsSource(Source):
    name = "hf_trending_models"

    def _fetch(self) -> list[Item]:
        headers = {}
        if HF_TOKEN:
            headers["Authorization"] = f"Bearer {HF_TOKEN}"

        resp = self._get(
            MODELS_URL,
            params={"sort": "trendingScore", "direction": -1, "limit": 30},
            headers=headers,
        )
        items: list[Item] = []
        for m in resp.json():
            model_id = m.get("modelId", m.get("id", ""))
            downloads = m.get("downloads", 0)
            likes = m.get("likes", 0)
            items.append(
                Item(
                    source="huggingface_trending",
                    type="model",
                    title=model_id,
                    url=f"https://huggingface.co/{model_id}",
                    tags=m.get("tags", []),
                    downloads=downloads,
                    likes=likes,
                    snippet=f"Trending model: {m.get('pipeline_tag', '?')} by {m.get('author', '?')}, {downloads:,} downloads",
                )
            )
        return items


class HFTrendingSpacesSource(Source):
    name = "hf_trending_spaces"

    def _fetch(self) -> list[Item]:
        headers = {}
        if HF_TOKEN:
            headers["Authorization"] = f"Bearer {HF_TOKEN}"

        resp = self._get(
            SPACES_URL,
            params={"sort": "trendingScore", "direction": -1, "limit": 20},
            headers=headers,
        )
        items: list[Item] = []
        for s in resp.json():
            space_id = s.get("id", "")
            items.append(
                Item(
                    source="huggingface_trending",
                    type="space",
                    title=s.get("title", space_id) or space_id,
                    url=f"https://huggingface.co/spaces/{space_id}",
                    likes=s.get("likes", 0),
                    snippet=f"Trending space by {s.get('author', '?')}",
                )
            )
        return items
