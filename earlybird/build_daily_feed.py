"""Build the daily feed JSON from all raw scrape files.

Reads today's raw_*.json files from data/, deduplicates, filters by keywords,
optionally enriches with Semantic Scholar citations, and writes daily-feed.json.

Usage:
    python -m earlybird.build_daily_feed
    python -m earlybird.build_daily_feed --enrich   # add citation counts
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
from datetime import datetime, timezone

from earlybird.config import DATA_DIR
from earlybird.models import DailyFeed, Item
from earlybird.pipeline.dedup import deduplicate
from earlybird.pipeline.filter import keyword_filter
from earlybird.pipeline.semantic_dedup import semantic_dedup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("earlybird")


def _load_today_raw() -> list[Item]:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pattern = str(DATA_DIR / f"raw_*_{today}.json")
    files = glob.glob(pattern)

    if not files:
        log.warning("no raw files found for %s, loading most recent", today)
        all_raw = sorted(glob.glob(str(DATA_DIR / "raw_*.json")))
        files = all_raw[-5:] if all_raw else []

    items: list[Item] = []
    for path in files:
        log.info("loading %s", path)
        with open(path) as f:
            data = json.load(f)
        for entry in data:
            items.append(Item(**entry))
    return items


def build() -> DailyFeed:
    raw = _load_today_raw()
    total_raw = len(raw)
    log.info("loaded %d raw items", total_raw)

    deduped = deduplicate(raw)
    log.info("after exact dedup: %d", len(deduped))

    deduped = semantic_dedup(deduped)
    total_dedup = len(deduped)
    log.info("after semantic dedup: %d", total_dedup)

    filtered = keyword_filter(deduped)
    total_filtered = len(filtered)
    log.info("after keyword filter: %d", total_filtered)

    return DailyFeed(
        total_raw=total_raw,
        total_after_dedup=total_dedup,
        total_after_filter=total_filtered,
        items=filtered,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build daily feed")
    parser.add_argument("--enrich", action="store_true", help="Enrich with Semantic Scholar citations")
    args = parser.parse_args()

    feed = build()

    if args.enrich:
        from earlybird.sources.semantic_scholar import SemanticScholarEnricher

        enricher = SemanticScholarEnricher()
        try:
            enricher.enrich(feed.items)
        finally:
            enricher.close()
        log.info("enriched with citation counts")

    out = DATA_DIR / "daily-feed.json"
    out.write_text(
        feed.model_dump_json(indent=2, exclude_none=True, exclude_defaults=True),
    )
    log.info("wrote %s (%d items)", out, len(feed.items))


if __name__ == "__main__":
    main()
