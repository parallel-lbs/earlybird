# Cron, Heartbeat & Ops Reference

## Schedule

All times UTC.

| Schedule | Command | Why this timing |
|---|---|---|
| `0 */6 * * *` | `python -m earlybird.scraper --sources arxiv` | ArXiv updates ~20:00 UTC daily. Every 6h catches it within one cycle. |
| `0 8,20 * * *` | `python -m earlybird.scraper --sources hf_papers` | HF papers appear during business hours. Twice covers EU + US windows. |
| `0 9 * * *` | `python -m earlybird.scraper --sources hf_trending` | Trending is slow-moving. Once daily is enough. |
| `0 10 * * *` | `python -m earlybird.scraper --sources pwc` | Papers With Code updates daily. |
| `0 */4 * * *` | `python -m earlybird.scraper --sources hn` | HN moves fast. Every 4h catches stories before they fall off. |
| `0 11 * * *` | `python -m earlybird.scraper --sources venture` | Crunchbase + YC + NFX. Deals/launches are daily events. |
| `0 12 * * 3` | `python -m earlybird.scraper --sources newsletters` | Newsletters drop on Wednesdays. |
| `0 12 * * 5` | `python -m earlybird.scraper --sources podcasts` | Podcast episodes drop on Fridays. |
| `30 6 * * *` | `python -m earlybird.build_daily_feed --enrich` | Build feed at 06:30 UTC, before morning digest. |

## Heartbeat logging

Wrap every cron command to record success/failure:

```bash
python -m earlybird.scraper --sources arxiv \
  && echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] OK arxiv $(wc -l < data/raw_arxiv_$(date -u +%Y-%m-%d).json) bytes" >> data/heartbeat.log \
  || echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] FAIL arxiv" >> data/heartbeat.log
```

### Check pipeline health

```bash
# Last 10 heartbeats
tail -10 data/heartbeat.log

# Failures today
grep "FAIL" data/heartbeat.log | grep "$(date -u +%Y-%m-%d)"

# Sources that haven't reported in 24h+
# Compare heartbeat timestamps against current time
```

## Troubleshooting

### Source returns 0 items

1. **ArXiv / HF Papers on weekends** — normal, these sources don't update on Sat/Sun.
2. **HN returns 0** — the keyword query filter may be too narrow for today's top stories. Check without the query filter:
   ```bash
   python -c "
   import httpx, time
   ts = int(time.time()) - 86400
   r = httpx.get('https://hn.algolia.com/api/v1/search', params={'tags':'story','numericFilters':f'points>100,created_at_i>{ts}','hitsPerPage':5})
   print(r.json().get('nbHits', 0), 'stories with 100+ points')
   "
   ```
3. **HF trending returns 400** — API may have changed sort parameters. Check current valid sort values.

### Source returns HTTP errors

| Code | Likely cause | Fix |
|---|---|---|
| 429 | Rate limited | Add/check API key in `.env`. Reduce scrape frequency. |
| 403 | Blocked / auth required | Check if API now requires a token. |
| 500+ | Upstream issue | Retry in 1h. If persistent 24h+, check source status page. |

### Feed is empty after build

1. Check that `data/raw_*.json` files exist for today: `ls data/raw_*_$(date -u +%Y-%m-%d).json`
2. If no files for today, builder falls back to most recent 5 files — check those exist.
3. If files exist but feed is empty, keyword filter may be too aggressive — inspect raw file contents.

### Heartbeat log missing

The `data/` directory or `heartbeat.log` doesn't exist yet. First cron run will create it. For manual init:

```bash
mkdir -p data && touch data/heartbeat.log
```
