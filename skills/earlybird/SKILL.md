---
name: earlybird
description: Operate and analyze the Earlybird content radar pipeline — fetch daily AI/tech feeds, rank items by novelty, signal strength, and founder relevance, prepare digests. Use when working with Earlybird feeds, signal filtering, content analysis, or daily digest preparation.
metadata:
  {
    "openclaw":
      {
        "emoji": "🐦",
        "requires": {},
      },
  }
---

# Earlybird — Content Radar

**Earlybird** is a content radar pipeline running at `api.8pilot.io`. It automatically scrapes 15 AI/tech sources on a cron schedule, deduplicates, filters, and produces a daily JSON feed.

Scraping and data collection run on the server automatically. Your job as the agent is to **fetch, analyze, rank, and deliver digests**.

## API

Base URL: `http://api.8pilot.io`

Auth header (required for all endpoints except `/health`):
```
Authorization: Bearer ASUEITsAgEfWKyxlXEgyT6Q6NcZnWUjawmWyQZbHKvI
```

| Method | Path | Body | Description |
|---|---|---|---|
| GET | `/health` | — | Server alive check |
| POST | `/scrape` | `{"sources": ["arxiv", "hn"]}` | Trigger manual scrape |
| POST | `/build` | `{"enrich": false}` | Rebuild daily feed |
| GET | `/feed?limit=50` | — | Get the daily feed |
| GET | `/feed/{item_id}` | — | Get single item by ID |
| GET | `/status` | — | Feed stats + heartbeat log |

Source groups: `arxiv`, `hf_papers`, `hf_trending`, `pwc`, `hn`, `venture`, `newsletters`, `podcasts`, `all`.

---

## Server-side cron (runs automatically)

Data collection is fully automated on the server. You do NOT need to trigger scrapes unless doing a manual refresh.

| Schedule (UTC) | Sources | Why |
|---|---|---|
| `0 */6 * * *` | `arxiv` | ArXiv updates ~20:00 UTC |
| `0 8,20 * * *` | `hf_papers` | EU + US business hours |
| `0 9 * * *` | `hf_trending` | Once daily |
| `0 10 * * *` | `pwc` | Papers With Code daily |
| `0 */4 * * *` | `hn` | HN moves fast |
| `0 11 * * *` | `venture` | Crunchbase + YC + NFX |
| `0 12 * * 3` | `newsletters` | Wednesdays |
| `0 12 * * 5` | `podcasts` | Fridays |
| `30 6 * * *` | build feed | Assembles daily-feed.json |

Heartbeat is logged to `data/heartbeat.log` on the server. Check via `GET /status`.

---

## Your workflow as the agent

### Morning digest (schedule at 07:00 UTC daily)

1. **Health check:**
   ```bash
   curl -s http://api.8pilot.io/health
   ```
   If server is down, report and stop.

2. **Fetch the feed** (cron already built it at 06:30):
   ```bash
   curl -s http://api.8pilot.io/feed?limit=50 \
     -H "Authorization: Bearer ASUEITsAgEfWKyxlXEgyT6Q6NcZnWUjawmWyQZbHKvI"
   ```

3. **Check pipeline health:**
   ```bash
   curl -s http://api.8pilot.io/status \
     -H "Authorization: Bearer ASUEITsAgEfWKyxlXEgyT6Q6NcZnWUjawmWyQZbHKvI"
   ```
   Check heartbeat — if any source has FAIL, note it in the digest.

4. **Analyze and rank.** Apply scoring heuristics below. Produce a ranked top 10.

5. **Prepare the digest.** For each item in top 10:
   - One-line summary: what it is + why it matters
   - Source and key signal (e.g. "42↑ on HF", "350pts on HN", "120★ GitHub")
   - Link

6. **Deliver** the digest to the user or target channel.

### Evening scan (schedule at 19:00 UTC daily)

Lighter pass — check for new high-signal items since the morning:

1. **Trigger fresh scrape** of fast-moving sources:
   ```bash
   curl -s -X POST http://api.8pilot.io/scrape \
     -H "Authorization: Bearer ASUEITsAgEfWKyxlXEgyT6Q6NcZnWUjawmWyQZbHKvI" \
     -H "Content-Type: application/json" \
     -d '{"sources": ["hn", "hf_papers"]}'
   ```

2. **Rebuild feed:**
   ```bash
   curl -s -X POST http://api.8pilot.io/build \
     -H "Authorization: Bearer ASUEITsAgEfWKyxlXEgyT6Q6NcZnWUjawmWyQZbHKvI" \
     -H "Content-Type: application/json" \
     -d '{"enrich": false}'
   ```

3. **Fetch and compare** against morning digest — surface only new items.

4. If 3+ genuinely new high-signal items, deliver a short evening update. Otherwise skip.

---

## Scoring & filtering

### What makes an item high-value

| Signal | Strong threshold | Why |
|---|---|---|
| HF upvotes | > 20 | ML practitioners voted |
| HN points | > 300 | Broad tech community validated |
| GitHub stars | > 100 | People are using it |
| Citation count | > 50 (within weeks) | Foundational work |
| Recency | Published within 48h | Fresh beats stale |
| Source authority | HF Papers > PWC > raw ArXiv | Community-filtered |
| Practical impact | Has repo, demo, benchmark | Can be built on |
| Novelty | New architecture, SOTA, capability | Changes what's possible |

### Signal combinations

- **Paper + trending model + HN discussion** = breakthrough
- **HF upvotes > 30 + GitHub repo** = immediately usable research
- **YC launch + HN 200+** = validated product in early traction
- **HN 500+ + no paper** = tool/product launch or industry event

### What to skip

- Surveys/reviews (unless > 100 citations)
- Incremental benchmarks (< 1% improvement)
- Company blog posts disguised as research
- Duplicate coverage across sources
- Theory with no code or application path
- "Fine-tuned X on Y" without methodological novelty

### Founder relevance lens

Prioritize through this lens:

1. **"Can I build on this?"** — new models, tools, APIs, infra
2. **"Does this change the market?"** — funding, launches, acquisitions
3. **"Should I know about this?"** — paradigm shifts, regulatory, talent
4. **"Is this a threat or opportunity?"** — competitors, adjacent moves

De-prioritize: pure theory, narrow domain, incremental academic work.

### Keyword taxonomy

For categorization:

- **Core AI:** LLM, transformer, attention, GPT, language model, foundation model, fine-tuning, RLHF, alignment
- **Methods:** diffusion, GAN, VAE, RL, RAG, agent, chain-of-thought, reasoning, MoE, distillation, quantization
- **Infra:** GPU, TPU, CUDA, distributed training, serving, latency, throughput, scaling
- **Business:** startup, funding, Series A/B, YC, open source, API, dev tools, moat, network effect
- **Emerging:** robotics, embodied, world model, synthetic data, code generation, autonomous, multimodal

---

## Sources (15)

| Source | Key | Frequency |
|---|---|---|
| ArXiv (cs.AI/LG/CL) | `arxiv` | Every 6h |
| HF Daily Papers | `hf_papers` | 2x/day |
| HF Trending Models | `hf_trending_models` | 1x/day |
| HF Trending Spaces | `hf_trending_spaces` | 1x/day |
| Papers With Code | `pwc` | 1x/day |
| Hacker News | `hackernews` | Every 4h |
| Crunchbase | `crunchbase` | 1x/day |
| YC Launches | `yc_launches` | 1x/day |
| NFX Essays | `nfx` | 1x/day |
| The Batch | `the_batch` | Wed |
| Import AI | `import_ai` | Wed |
| Interconnects | `interconnects` | Wed |
| Latent Space | `latent_space` | Fri |
| Lex Fridman | `lex_fridman` | Fri |
| Acquired | `acquired` | Fri |

---

## Feed JSON schema

```json
{
  "scraped_at": "2026-03-29T06:30:00Z",
  "total_raw": 387,
  "total_after_dedup": 201,
  "total_after_filter": 48,
  "items": [
    {
      "id": "arxiv:2603.12345",
      "source": "huggingface_papers",
      "title": "...",
      "abstract": "...",
      "url": "https://huggingface.co/papers/2603.12345",
      "upvotes": 34,
      "published": "2026-03-28"
    }
  ]
}
```

Item fields: `id`, `source`, `title`, `url`, `abstract`, `snippet`, `description`, `authors`, `category`, `pdf_url`, `arxiv_url`, `github_url`, `upvotes`, `github_stars`, `hn_points`, `hn_comments`, `citation_count`, `downloads`, `likes`, `type`, `tags`, `duration`, `published`, `scraped_at`.

---

## Troubleshooting

**Feed empty or stale:**
1. `GET /status` — check heartbeat. If sources show FAIL, note which ones.
2. If all sources FAIL — server may be down. Try `GET /health`.
3. Trigger manual scrape: `POST /scrape {"sources": ["all"]}`, then `POST /build`.

**Source returns 0 items:**
- ArXiv / HF Papers on weekends — normal.
- HN 0 items — keyword filter too narrow for today.

**Server unreachable:** Report to the user. Server is at `158.160.193.93`, service name `earlybird`.
