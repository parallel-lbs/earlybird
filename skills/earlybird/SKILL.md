---
name: earlybird
description: Operate and analyze the Earlybird content radar pipeline — run source scrapers, build and inspect daily feeds, manage cron schedules, troubleshoot source failures, add new sources, and rank AI/tech items by novelty, signal strength, and practical founder relevance. Use when working with Earlybird feeds, source collection, signal filtering, or daily digest preparation.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, CronCreate, CronList
---

# Earlybird — Content Radar

You are operating **Earlybird**, a content radar pipeline that collects AI/tech items from 15 sources, deduplicates (exact + semantic cosine similarity), filters by keywords, and produces a daily JSON feed.

**This skill covers operations and analysis.** Final scoring and digest generation may be handled by a separate prompt or agent — this skill prepares, filters, and interprets the data for that stage.

## Project location

```
!`echo $PWD`
```

## Standard workflow

1. Confirm you are in the Earlybird repo root.
2. Run or inspect the relevant source scrapers.
3. Build `data/daily-feed.json`.
4. Inspect feed counts and a small sample of items.
5. Apply filtering heuristics (see [scoring reference](references/scoring.md)):
   - prioritize recency
   - prioritize strong community validation
   - prefer practical, buildable signals
   - skip weak incremental work and duplicated coverage
6. If needed, prepare a shortlist or digest for founder review.
7. If a source is missing or failing, check [cron reference](references/cron.md) for heartbeat logs and troubleshooting.

## Quick commands

### Scrape sources

```bash
# Single group
python -m earlybird.scraper --sources arxiv
python -m earlybird.scraper --sources hn
python -m earlybird.scraper --sources hf_papers hf_trending

# All sources at once
python -m earlybird.scraper --sources all
```

**Source groups:** `arxiv`, `hf_papers`, `hf_trending`, `pwc`, `hn`, `venture`, `newsletters`, `podcasts`, `all`.

### Build the daily feed

```bash
# Standard
python -m earlybird.build_daily_feed

# With Semantic Scholar citation enrichment (needs SEMANTIC_SCHOLAR_API_KEY for 200+ papers)
python -m earlybird.build_daily_feed --enrich
```

Output: `data/daily-feed.json`

### Read the feed

```bash
python -c "
import json
with open('data/daily-feed.json') as f:
    feed = json.load(f)
print(f'Items: {feed[\"total_after_filter\"]}')
for it in feed['items'][:10]:
    src = it['source']
    title = it['title'][:80]
    signals = []
    if it.get('upvotes'): signals.append(f'{it[\"upvotes\"]}↑')
    if it.get('hn_points'): signals.append(f'{it[\"hn_points\"]}pts')
    if it.get('github_stars'): signals.append(f'{it[\"github_stars\"]}★')
    if it.get('citation_count'): signals.append(f'{it[\"citation_count\"]} cites')
    sig = ' '.join(signals)
    print(f'  [{src}] {title}  {sig}')
"
```

## References

| Topic | File | When to read |
|---|---|---|
| Signal scoring & filtering | [references/scoring.md](references/scoring.md) | Evaluating items, building shortlists, deciding what to skip |
| Cron, heartbeat & ops | [references/cron.md](references/cron.md) | Setting up schedules, checking pipeline health, troubleshooting failures |
| Sources & extensibility | [references/sources.md](references/sources.md) | Adding new sources, understanding the feed schema, modifying the registry |
