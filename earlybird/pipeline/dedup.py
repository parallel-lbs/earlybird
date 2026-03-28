from __future__ import annotations

import hashlib
import re

from earlybird.models import Item

# Sources ordered by signal richness — first match wins on collision.
_SOURCE_PRIORITY = {
    "huggingface_papers": 0,
    "papers_with_code": 1,
    "arxiv": 2,
}


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]", "", title.lower())


def dedup_key(item: Item) -> str:
    """Return a stable dedup key. ArXiv ID for papers, title hash otherwise."""
    urls = " ".join([item.url, item.arxiv_url, item.pdf_url])
    arxiv_match = re.search(r"(\d{4}\.\d{4,5})", urls)
    if arxiv_match:
        return f"arxiv:{arxiv_match.group(1)}"
    return hashlib.md5(_normalize_title(item.title).encode()).hexdigest()


def deduplicate(items: list[Item]) -> list[Item]:
    """Remove duplicates, keeping the item from the highest-priority source."""
    seen: dict[str, Item] = {}
    for item in items:
        key = dedup_key(item)

        if item.id and not item.id.startswith("arxiv:"):
            pass  # keep generated id
        if key.startswith("arxiv:"):
            item.id = key

        if key in seen:
            existing = seen[key]
            existing_prio = _SOURCE_PRIORITY.get(existing.source, 99)
            new_prio = _SOURCE_PRIORITY.get(item.source, 99)
            if new_prio < existing_prio:
                # Merge signals from the lower-priority item
                _merge_signals(target=item, donor=existing)
                seen[key] = item
            else:
                _merge_signals(target=existing, donor=item)
        else:
            seen[key] = item

    return list(seen.values())


def _merge_signals(target: Item, donor: Item) -> None:
    """Copy non-null signals from donor into target."""
    if donor.upvotes and not target.upvotes:
        target.upvotes = donor.upvotes
    if donor.github_stars and not target.github_stars:
        target.github_stars = donor.github_stars
    if donor.hn_points and not target.hn_points:
        target.hn_points = donor.hn_points
    if donor.citation_count and not target.citation_count:
        target.citation_count = donor.citation_count
    if donor.github_url and not target.github_url:
        target.github_url = donor.github_url
