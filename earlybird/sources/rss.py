"""RSS/Atom-based sources: Crunchbase, YC Launches, NFX, newsletters, podcasts."""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone

import feedparser

from earlybird.config import CRUNCHBASE_KEYWORDS, LEX_KEYWORDS
from earlybird.models import Item
from earlybird.sources.base import Source

# Only keep RSS items published within the last N days
RSS_MAX_AGE_DAYS = 7


def _strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html).strip()


def _matches_keywords(text: str, keywords: list[str]) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def _is_recent(entry, max_age_days: int = RSS_MAX_AGE_DAYS) -> bool:
    """Return True if the entry was published within max_age_days."""
    published = entry.get("published_parsed") or entry.get("updated_parsed")
    if not published:
        return True  # no date = keep it
    try:
        pub_ts = time.mktime(published)
        age_days = (time.time() - pub_ts) / 86400
        return age_days <= max_age_days
    except (ValueError, OverflowError):
        return True


class _RSSSource(Source):
    """Generic RSS source — subclass sets name, feed_url, and optionally overrides _to_item."""

    feed_url: str

    def _fetch(self) -> list[Item]:
        feed = feedparser.parse(self.feed_url)
        items: list[Item] = []
        for entry in feed.entries:
            if not _is_recent(entry):
                continue
            item = self._to_item(entry)
            if item is not None:
                items.append(item)
        return items

    def _to_item(self, entry) -> Item | None:
        return Item(
            source=self.name,
            title=entry.get("title", ""),
            url=entry.get("link", ""),
            snippet=_strip_html(entry.get("summary", "")),
            published=entry.get("published", ""),
        )


# ── Venture & startups ──────────────────────────────────────────────────────


class CrunchbaseSource(_RSSSource):
    name = "crunchbase"
    feed_url = "https://news.crunchbase.com/feed/"

    def _to_item(self, entry) -> Item | None:
        title = entry.get("title", "")
        summary = _strip_html(entry.get("summary", ""))
        if not _matches_keywords(f"{title} {summary}", CRUNCHBASE_KEYWORDS):
            return None
        return Item(
            source=self.name,
            title=title,
            url=entry.get("link", ""),
            snippet=summary,
            published=entry.get("published", ""),
        )


class YCLaunchesSource(_RSSSource):
    name = "yc_launches"
    feed_url = "https://www.ycombinator.com/launches.atom"

    def _to_item(self, entry) -> Item | None:
        return Item(
            source=self.name,
            title=entry.get("title", ""),
            url=entry.get("link", ""),
            description=_strip_html(entry.get("summary", "")),
            published=entry.get("published", ""),
        )


class NFXSource(_RSSSource):
    name = "nfx"
    feed_url = "https://www.nfx.com/feed.xml"


# ── Newsletters ──────────────────────────────────────────────────────────────


class TheBatchSource(_RSSSource):
    name = "the_batch"
    feed_url = "https://www.deeplearning.ai/the-batch/feed/"


class ImportAISource(_RSSSource):
    name = "import_ai"
    feed_url = "https://importai.substack.com/feed"


class InterconnectsSource(_RSSSource):
    name = "interconnects"
    feed_url = "https://www.interconnects.ai/feed"


# ── Podcasts ─────────────────────────────────────────────────────────────────


class LatentSpaceSource(_RSSSource):
    name = "latent_space"
    feed_url = "https://api.substack.com/feed/podcast/1084089/s/71556"

    def _to_item(self, entry) -> Item | None:
        return Item(
            source="latent_space_podcast",
            title=entry.get("title", ""),
            url=entry.get("link", ""),
            description=_strip_html(entry.get("summary", "")),
            duration=entry.get("itunes_duration", ""),
            published=entry.get("published", ""),
        )


class LexFridmanSource(_RSSSource):
    name = "lex_fridman"
    feed_url = "https://lexfridman.com/feed/podcast/"

    def _to_item(self, entry) -> Item | None:
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        if not _matches_keywords(f"{title} {summary}", LEX_KEYWORDS):
            return None
        return Item(
            source="lex_fridman_podcast",
            title=title,
            url=entry.get("link", ""),
            description=_strip_html(summary),
            duration=entry.get("itunes_duration", ""),
            published=entry.get("published", ""),
        )


class AcquiredSource(_RSSSource):
    name = "acquired"
    feed_url = "https://feeds.pacific-content.com/acquired"

    def _to_item(self, entry) -> Item | None:
        return Item(
            source="acquired_podcast",
            title=entry.get("title", ""),
            url=entry.get("link", ""),
            description=_strip_html(entry.get("summary", "")),
            duration=entry.get("itunes_duration", ""),
            published=entry.get("published", ""),
        )
