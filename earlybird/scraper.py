"""CLI entry point: scrape one or more source groups.

Usage:
    python -m earlybird.scraper --sources arxiv hf_papers hn
    python -m earlybird.scraper --sources all
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from earlybird.config import DATA_DIR, SOURCE_GROUPS
from earlybird.models import Item
from earlybird.sources.registry import REGISTRY, get_source

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("earlybird")


def _resolve_sources(groups: list[str]) -> list[str]:
    """Expand group names (e.g. 'venture') into individual source names."""
    names: list[str] = []
    for g in groups:
        if g in SOURCE_GROUPS:
            names.extend(SOURCE_GROUPS[g])
        elif g in REGISTRY:
            names.append(g)
        else:
            log.warning("unknown source/group: %s (skipping)", g)
    return list(dict.fromkeys(names))  # dedupe, preserve order


def scrape(source_names: list[str]) -> list[Item]:
    items: list[Item] = []
    for name in source_names:
        source = get_source(name)
        try:
            items.extend(source.fetch())
        finally:
            source.close()
    return items


def _save(items: list[Item], tag: str) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = DATA_DIR / f"raw_{tag}_{ts}.json"
    payload = [it.model_dump(exclude_none=True, exclude_defaults=True) for it in items]
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    log.info("saved %d items → %s", len(items), out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Earlybird scraper")
    parser.add_argument(
        "--sources",
        nargs="+",
        required=True,
        help=f"Source groups to scrape: {', '.join(SOURCE_GROUPS)}",
    )
    args = parser.parse_args()

    source_names = _resolve_sources(args.sources)
    if not source_names:
        log.error("no valid sources specified")
        sys.exit(1)

    log.info("scraping: %s", ", ".join(source_names))
    items = scrape(source_names)
    tag = "_".join(args.sources)
    _save(items, tag)


if __name__ == "__main__":
    main()
