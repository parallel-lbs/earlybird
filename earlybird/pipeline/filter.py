from __future__ import annotations

import re

from earlybird.config import KEYWORDS
from earlybird.models import Item

_PATTERN = re.compile(
    "|".join(re.escape(kw) for kw in KEYWORDS),
    re.IGNORECASE,
)

# Sources that are already curated — skip keyword filter for them.
_CURATED_SOURCES = {
    "huggingface_trending",
    "latent_space_podcast",
    "lex_fridman_podcast",
    "acquired_podcast",
    "the_batch",
    "import_ai",
    "interconnects",
    "nfx",
}


def keyword_filter(items: list[Item]) -> list[Item]:
    """Keep items that contain at least one keyword in title + abstract/snippet.

    Curated sources (newsletters, podcasts, trending) bypass this filter.
    """
    result: list[Item] = []
    for item in items:
        if item.source in _CURATED_SOURCES:
            result.append(item)
            continue
        text = f"{item.title} {item.abstract} {item.snippet} {item.description}"
        if _PATTERN.search(text):
            result.append(item)
    return result
