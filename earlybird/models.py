from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Item(BaseModel):
    """Universal item collected from any source."""

    id: str = ""
    source: str
    title: str
    url: str
    abstract: str = ""
    snippet: str = ""

    # Paper-specific
    authors: list[str] = Field(default_factory=list)
    category: str = ""
    pdf_url: str = ""
    arxiv_url: str = ""
    github_url: str = ""

    # Signals
    upvotes: int | None = None
    github_stars: int | None = None
    hn_points: int | None = None
    hn_comments: int | None = None
    citation_count: int | None = None
    downloads: int | None = None
    likes: int | None = None

    # HF trending
    type: str = ""  # "model" | "space" | "paper" | ""
    tags: list[str] = Field(default_factory=list)

    # Podcast
    duration: str = ""
    description: str = ""

    # Timestamps
    published: str = ""
    scraped_at: str = Field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))

    # Arbitrary extra data
    extra: dict[str, Any] = Field(default_factory=dict)


class DailyFeed(BaseModel):
    """Aggregated daily feed sent to LLM agent."""

    scraped_at: str = Field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
    total_raw: int = 0
    total_after_dedup: int = 0
    total_after_filter: int = 0
    items: list[Item] = Field(default_factory=list)
