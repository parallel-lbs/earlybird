# Sources & Extensibility Reference

## Current sources (15)

| Source | Key | Type | Frequency |
|---|---|---|---|
| ArXiv (cs.AI/LG/CL) | `arxiv` | API (Atom XML) | Every 6h |
| HF Daily Papers | `hf_papers` | API (JSON) | 2x/day |
| HF Trending Models | `hf_trending_models` | API (JSON) | 1x/day |
| HF Trending Spaces | `hf_trending_spaces` | API (JSON) | 1x/day |
| Papers With Code | `pwc` | API (JSON) | 1x/day |
| Hacker News | `hackernews` | Algolia API | Every 4h |
| Crunchbase | `crunchbase` | RSS | 1x/day |
| YC Launches | `yc_launches` | Atom feed | 1x/day |
| NFX Essays | `nfx` | RSS | 1x/day |
| The Batch | `the_batch` | RSS | Wednesdays |
| Import AI | `import_ai` | RSS | Wednesdays |
| Interconnects | `interconnects` | RSS | Wednesdays |
| Latent Space | `latent_space` | RSS | Fridays |
| Lex Fridman | `lex_fridman` | RSS (filtered) | Fridays |
| Acquired | `acquired` | RSS | Fridays |

**Enrichment (not a scrape source):** Semantic Scholar — batch citation counts for top paper candidates.

## Source groups

Defined in `earlybird/config.py` → `SOURCE_GROUPS`:

```
arxiv        → [arxiv]
hf_papers    → [hf_papers]
hf_trending  → [hf_trending_models, hf_trending_spaces]
pwc          → [pwc]
hn           → [hackernews]
venture      → [crunchbase, yc_launches, nfx]
newsletters  → [the_batch, import_ai, interconnects]
podcasts     → [latent_space, lex_fridman, acquired]
all          → (all of the above)
```

## Adding a new source

### Step 1: Create the source class

Create `earlybird/sources/my_source.py`:

```python
from earlybird.models import Item
from earlybird.sources.base import Source


class MySource(Source):
    name = "my_source"

    def _fetch(self) -> list[Item]:
        resp = self._get("https://api.example.com/feed")
        data = resp.json()
        return [
            Item(
                source=self.name,
                title=entry["title"],
                url=entry["url"],
                snippet=entry.get("description", ""),
                published=entry.get("date", ""),
            )
            for entry in data
        ]
```

For RSS sources, it's even simpler — subclass `_RSSSource` in `earlybird/sources/rss.py`:

```python
class MyRSSSource(_RSSSource):
    name = "my_source"
    feed_url = "https://example.com/feed.xml"
```

### Step 2: Register

Add to `earlybird/sources/registry.py`:

```python
from earlybird.sources.my_source import MySource

REGISTRY["my_source"] = MySource
```

### Step 3: Add to a group (optional)

In `earlybird/config.py`, add to an existing group or create a new one:

```python
SOURCE_GROUPS["my_group"] = ["my_source"]
```

### Step 4: Test

```bash
python -m earlybird.scraper --sources my_source
cat data/raw_my_source_$(date -u +%Y-%m-%d).json | python -m json.tool | head -20
```

## Pipeline stages

```
Sources (15)
    ↓ scraper.py writes raw_<group>_<date>.json per run
    ↓
build_daily_feed.py reads all raw files for today
    ↓
Exact dedup (ArXiv ID match + title hash)
    ↓
Semantic dedup (cosine similarity > 0.93 on title embeddings, all-MiniLM-L6-v2)
    ↓
Keyword filter (curated sources like newsletters/podcasts bypass this)
    ↓
[Optional] Semantic Scholar enrichment (--enrich flag)
    ↓
data/daily-feed.json
```

## Dedup priority

When two items collide (same ArXiv ID or near-identical title), the item from the higher-priority source wins. Signals from the losing item are merged into the winner.

Priority: `huggingface_papers` > `papers_with_code` > `arxiv` > everything else.

## Feed JSON schema

Output `daily-feed.json`:

```json
{
  "scraped_at": "2026-03-29T06:30:00Z",
  "total_raw": 387,
  "total_after_dedup": 201,
  "total_after_filter": 48,
  "items": [...]
}
```

Each item may have these fields:

| Field | Type | Present when |
|---|---|---|
| `id` | string | Papers (format: `arxiv:XXXX.XXXXX`) |
| `source` | string | Always |
| `title` | string | Always |
| `url` | string | Always |
| `abstract` | string | Papers |
| `snippet` | string | RSS sources |
| `description` | string | Podcasts, YC launches |
| `authors` | string[] | Papers |
| `category` | string | ArXiv papers |
| `pdf_url` | string | Papers |
| `arxiv_url` | string | HF papers |
| `github_url` | string | PWC papers |
| `upvotes` | int | HF papers |
| `github_stars` | int | PWC papers |
| `hn_points` | int | HN stories |
| `hn_comments` | int | HN stories |
| `citation_count` | int | After enrichment |
| `downloads` | int | HF trending models |
| `likes` | int | HF trending |
| `type` | string | HF trending (`model` / `space`) |
| `tags` | string[] | HF trending models |
| `duration` | string | Podcasts |
| `published` | string | Always |
| `scraped_at` | string | Always |

## Adapting for non-AI domains

The architecture is domain-agnostic. To track a different niche (crypto, biotech, climate, etc.):

1. Replace or add sources in `earlybird/sources/`
2. Update `KEYWORDS` in `earlybird/config.py` to match your domain
3. Update keyword filters in `config.py` (`CRUNCHBASE_KEYWORDS`, `LEX_KEYWORDS`) if applicable
4. Adjust `_CURATED_SOURCES` in `earlybird/pipeline/filter.py` for sources that should bypass keyword filtering
