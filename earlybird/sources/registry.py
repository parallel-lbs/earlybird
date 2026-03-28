from __future__ import annotations

from earlybird.sources.arxiv import ArxivSource
from earlybird.sources.base import Source
from earlybird.sources.hackernews import HackerNewsSource
from earlybird.sources.hf_papers import HFPapersSource
from earlybird.sources.hf_trending import HFTrendingModelsSource, HFTrendingSpacesSource
from earlybird.sources.pwc import PapersWithCodeSource
from earlybird.sources.rss import (
    AcquiredSource,
    CrunchbaseSource,
    ImportAISource,
    InterconnectsSource,
    LatentSpaceSource,
    LexFridmanSource,
    NFXSource,
    TheBatchSource,
    YCLaunchesSource,
)

REGISTRY: dict[str, type[Source]] = {
    "arxiv": ArxivSource,
    "hf_papers": HFPapersSource,
    "hf_trending_models": HFTrendingModelsSource,
    "hf_trending_spaces": HFTrendingSpacesSource,
    "pwc": PapersWithCodeSource,
    "hackernews": HackerNewsSource,
    "crunchbase": CrunchbaseSource,
    "yc_launches": YCLaunchesSource,
    "nfx": NFXSource,
    "the_batch": TheBatchSource,
    "import_ai": ImportAISource,
    "interconnects": InterconnectsSource,
    "latent_space": LatentSpaceSource,
    "lex_fridman": LexFridmanSource,
    "acquired": AcquiredSource,
}


def get_source(name: str) -> Source:
    cls = REGISTRY[name]
    return cls()
