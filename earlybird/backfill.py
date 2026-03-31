"""Historical backfill: fetch ArXiv + HF Papers for the last N days.

CLI usage:
    python -m earlybird.backfill --days 365 --sources arxiv hf_papers
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from earlybird.config import BACKFILL_DIR
from earlybird.models import Item

log = logging.getLogger(__name__)


def run_backfill(
    days: int = 365,
    sources: list[str] | None = None,
) -> Path:
    """Run historical backfill and save results.

    Args:
        days: number of days to look back
        sources: list of source names (default: ["arxiv", "hf_papers"])

    Returns:
        Path to the saved backfill JSON file.
    """
    if sources is None:
        sources = ["arxiv", "hf_papers"]

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    log.info(
        "starting backfill: %s to %s, sources=%s",
        start_str,
        end_str,
        sources,
    )

    all_items: list[Item] = []
    seen_ids: set[str] = set()

    def _add_items(items: list[Item]) -> int:
        added = 0
        for item in items:
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                all_items.append(item)
                added += 1
        return added

    # ── ArXiv backfill ──────────────────────────────────────────────────
    if "arxiv" in sources:
        log.info("backfill: starting arxiv fetch")
        from earlybird.sources.arxiv import ArxivSource

        arxiv = ArxivSource()
        try:
            items = arxiv.fetch_range(start_str, end_str, max_total=5000)
            added = _add_items(items)
            log.info("backfill: arxiv contributed %d new items", added)
        except Exception:
            log.exception("backfill: arxiv fetch failed")
        finally:
            arxiv.close()

    # ── HF Papers backfill (day-by-day) ─────────────────────────────────
    if "hf_papers" in sources:
        log.info("backfill: starting hf_papers fetch")
        from earlybird.sources.hf_papers import HFPapersSource

        hf = HFPapersSource()
        try:
            cursor = start_date
            day_count = 0
            while cursor <= end_date:
                date_str = cursor.strftime("%Y-%m-%d")
                try:
                    items = hf.fetch_date(date_str, min_upvotes=3)
                    added = _add_items(items)
                    if added:
                        log.debug("hf_papers %s: +%d items", date_str, added)
                except Exception:
                    log.warning("hf_papers failed for %s, skipping", date_str)

                day_count += 1
                if day_count % 30 == 0:
                    log.info(
                        "hf_papers progress: %d/%d days, %d total items",
                        day_count,
                        days,
                        len(all_items),
                    )

                cursor += timedelta(days=1)
                time.sleep(1)  # rate limit
        except Exception:
            log.exception("backfill: hf_papers fetch failed")
        finally:
            hf.close()

    # ── Save ────────────────────────────────────────────────────────────
    log.info("backfill complete: %d unique items", len(all_items))

    out_path = BACKFILL_DIR / "backfill.json"
    data = [item.model_dump() for item in all_items]
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    log.info("saved backfill → %s", out_path)

    return out_path


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="Earlybird historical backfill")
    parser.add_argument("--days", type=int, default=365, help="days to look back")
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["arxiv", "hf_papers"],
        choices=["arxiv", "hf_papers"],
        help="sources to backfill",
    )
    args = parser.parse_args()

    run_backfill(days=args.days, sources=args.sources)


if __name__ == "__main__":
    main()
