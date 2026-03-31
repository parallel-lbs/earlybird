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

Scraping and data collection run on the server automatically. Your job as the agent is to **configure preferences, schedule jobs, fetch feeds, analyze, rank, and deliver digests**.

---

## First run setup

On first use, check if a preferences file exists at `~/.earlybird/preferences.json`.

**If it does NOT exist**, ask the user the following questions. If the user skips any question, use the default.

| Question | Default | Saved as |
|---|---|---|
| What topics do you care about? | `["AI/ML", "startups", "infrastructure"]` | `topics` |
| Morning digest time? | `07:00 UTC` | `morning_time` |
| Evening scan time? (or skip) | `19:00 UTC` | `evening_time` |
| Timezone? | `UTC` | `timezone` |
| Digest format: short (1-line per item) or detailed (summary + why it matters)? | `detailed` | `format` |
| How many items in the digest? | `10` | `top_n` |
| Delivery channel? (this chat / specific channel) | `this chat` | `channel` |
| Any keywords to always include, even if low signal? | `[]` | `must_include_keywords` |
| Any keywords to always exclude? | `[]` | `exclude_keywords` |

After collecting answers, save:

```bash
mkdir -p ~/.earlybird
cat > ~/.earlybird/preferences.json << 'EOF'
{
  "topics": ["AI/ML", "startups", "infrastructure"],
  "morning_time": "07:00",
  "evening_time": "19:00",
  "timezone": "UTC",
  "format": "detailed",
  "top_n": 10,
  "channel": "this chat",
  "must_include_keywords": [],
  "exclude_keywords": []
}
EOF
```

Then set up scheduled jobs based on the user's preferred times (see Scheduled jobs section).

**If preferences already exist**, load them and proceed to the workflow.

To reconfigure later, the user can say "reconfigure earlybird" or "change earlybird settings".

---

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

## Scheduled jobs

Set up these jobs based on user preferences. Use `openclaw cron add` or the platform's scheduler.

### Morning digest

**Schedule:** user's `morning_time` (default 07:00 UTC daily)
**Job name:** `earlybird:morning-digest`

Steps:

1. `GET /health` — if down, report and stop.
2. `GET /feed?limit={top_n * 3}` — fetch candidates (3x top_n to have room for filtering).
3. `GET /status` — check heartbeat for failures.
4. Apply scoring heuristics (see below) filtered by user's `topics`, `must_include_keywords`, `exclude_keywords`.
5. Rank and select top `{top_n}` items.
6. Format digest according to `{format}` preference:
   - **short:** `[source] Title (signal) — link`
   - **detailed:** Title, one-line summary, why it matters, source + signal, link
7. Deliver to `{channel}`.

### Evening scan

**Schedule:** user's `evening_time` (default 19:00 UTC daily)
**Job name:** `earlybird:evening-scan`

Steps:

1. `POST /scrape {"sources": ["hn", "hf_papers"]}` — refresh fast-moving sources.
2. `POST /build {"enrich": false}` — rebuild.
3. `GET /feed?limit=20` — fetch latest.
4. Compare against morning digest — only surface **new** items.
5. If 3+ new high-signal items, deliver a short update. Otherwise skip silently.

---

## Server-side cron (runs automatically)

Data collection runs on the server. You do NOT need to trigger scrapes unless doing a manual refresh.

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

Check health via `GET /status`.

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

### Applying user preferences

When scoring, also apply:

- **`topics`** — boost items matching user's topics
- **`must_include_keywords`** — always include items with these keywords regardless of score
- **`exclude_keywords`** — always drop items with these keywords
- If user has a specific role (founder, researcher, engineer), adjust the relevance lens accordingly

### Founder relevance lens (default)

1. **"Can I build on this?"** — new models, tools, APIs, infra
2. **"Does this change the market?"** — funding, launches, acquisitions
3. **"Should I know about this?"** — paradigm shifts, regulatory, talent
4. **"Is this a threat or opportunity?"** — competitors, adjacent moves

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
1. `GET /status` — check heartbeat.
2. If all FAIL — `GET /health`. If down, report to user.
3. Manual refresh: `POST /scrape {"sources": ["all"]}`, then `POST /build`.

**Source returns 0 items:**
- ArXiv / HF Papers on weekends — normal.
- HN 0 items — keyword filter too narrow.

**Server unreachable:** Report to user. Server at `158.160.193.93`, service `earlybird`.
