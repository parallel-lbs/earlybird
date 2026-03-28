# Earlybird

Content radar for AI/tech — scrapes ~300-400 items/day from 15 sources, deduplicates, filters by keywords, and outputs a clean JSON feed for LLM scoring.

## Sources

| Category | Sources |
|---|---|
| Research papers | ArXiv (cs.AI/LG/CL), HF Daily Papers, HF Trending Models & Spaces, Papers With Code |
| Daily signal | Hacker News (100+ points) |
| Venture & startups | Crunchbase RSS, YC Launches, NFX Essays |
| Newsletters | The Batch, Import AI, Interconnects |
| Podcasts | Latent Space, Lex Fridman, Acquired |

Enrichment: Semantic Scholar (citation counts for top candidates).

## Setup

```bash
pip install -e .
```

Optional env vars (`.env`):

```
HF_TOKEN=hf_...                   # higher HF rate limits
SEMANTIC_SCHOLAR_API_KEY=...       # higher S2 rate limits
EARLYBIRD_DATA_DIR=./data          # output directory (default: ./data)
```

## Usage

### Scrape

```bash
# Single source group
python -m earlybird.scraper --sources arxiv
python -m earlybird.scraper --sources hn
python -m earlybird.scraper --sources hf_papers hf_trending

# All sources at once
python -m earlybird.scraper --sources all
```

Source groups: `arxiv`, `hf_papers`, `hf_trending`, `pwc`, `hn`, `venture`, `newsletters`, `podcasts`, `all`.

### Build daily feed

Aggregates all raw files for today, deduplicates, and applies keyword filter:

```bash
python -m earlybird.build_daily_feed

# With Semantic Scholar citation enrichment
python -m earlybird.build_daily_feed --enrich
```

Output: `data/daily-feed.json`

### Cron schedule

```cron
0 */6 * * *   python -m earlybird.scraper --sources arxiv
0 8,20 * * *  python -m earlybird.scraper --sources hf_papers
0 9 * * *     python -m earlybird.scraper --sources hf_trending
0 10 * * *    python -m earlybird.scraper --sources pwc
0 */4 * * *   python -m earlybird.scraper --sources hn
0 11 * * *    python -m earlybird.scraper --sources venture
0 12 * * 3    python -m earlybird.scraper --sources newsletters
0 12 * * 5    python -m earlybird.scraper --sources podcasts
30 6 * * *    python -m earlybird.build_daily_feed --enrich
```

## Pipeline

```
Sources (15) → raw JSON files per group
                    ↓
            build_daily_feed
                    ↓
        Dedup (ArXiv ID / title hash, signal merging)
                    ↓
        Keyword filter (curated sources bypass)
                    ↓
        [Optional] Semantic Scholar enrichment
                    ↓
            data/daily-feed.json → LLM agent → Telegram digest
```

## Architecture

```
earlybird/
├── config.py              # paths, keys, keywords, source groups
├── models.py              # Item + DailyFeed (Pydantic)
├── scraper.py             # CLI: scrape by source group
├── build_daily_feed.py    # CLI: aggregate → dedup → filter → feed
├── sources/
│   ├── base.py            # abstract Source (httpx client)
│   ├── registry.py        # name → class mapping
│   ├── arxiv.py           # ArXiv Atom XML
│   ├── hf_papers.py       # HF Daily Papers API
│   ├── hf_trending.py     # HF trending models + spaces
│   ├── pwc.py             # Papers With Code API
│   ├── semantic_scholar.py# citation enrichment (batch)
│   ├── hackernews.py      # HN Algolia API
│   └── rss.py             # 8 RSS sources (venture, newsletters, podcasts)
└── pipeline/
    ├── dedup.py           # ArXiv ID + title hash, priority-based merging
    └── filter.py          # keyword pre-filter
```

## Cost

$0/month. All sources are free APIs / RSS feeds.
