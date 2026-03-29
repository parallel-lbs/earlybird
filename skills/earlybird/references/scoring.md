# Scoring & Filtering Reference

## What makes an item high-value

Score items by these signals, strongest first:

| Signal | Strong threshold | Why it matters |
|---|---|---|
| HF upvotes | > 20 | ML practitioners voted — this paper is practically useful |
| HN points | > 300 | Broad tech community validated it |
| GitHub stars | > 100 | People are actually using/building on it |
| Citation count | > 50 (within weeks of publication) | Academic community considers it foundational |
| Recency | Published within 48h | Fresh signal beats stale signal |
| Source authority | HF Papers > PWC > raw ArXiv | Higher = already community-filtered |
| Practical impact | Has repo, demo, or benchmark | Can be reproduced, built on, or integrated |
| Novelty | New architecture, SOTA, or capability | Not incremental — changes what's possible |

## Signal combinations

Items with multiple strong signals are almost always worth surfacing:

- **Paper + trending model + HN discussion** = breakthrough (e.g. new architecture release)
- **HF upvotes > 30 + GitHub repo** = immediately usable research
- **YC launch + HN 200+ points** = validated product in early traction
- **HN 500+ points + no paper** = likely tool/product launch or industry event

## What to skip

- Surveys and review papers (unless comprehensive and well-cited, > 100 citations)
- Incremental benchmarks with < 1% improvement over SOTA
- Company blog posts disguised as research (check: are there actual experiments?)
- Duplicate coverage of the same announcement across HN + newsletters + papers
- Theoretical work with no experiments, no code, no clear path to application
- "We fine-tuned X on Y" without meaningful novelty in method or result

## Keyword taxonomy

The scraper pre-filters by these keyword families. Use them for categorization and further filtering:

### Core AI
LLM, transformer, attention, GPT, language model, foundation model, fine-tuning, RLHF, alignment, inference, training, benchmark, evaluation

### Methods
diffusion, GAN, VAE, reinforcement learning, multi-modal, vision-language, embedding, retrieval, RAG, agent, chain-of-thought, reasoning, mixture of experts, MoE, distillation, quantization

### Infrastructure
GPU, TPU, CUDA, distributed training, serving, latency, throughput, scaling, infrastructure

### Business
startup, funding, Series A, Series B, YC, open source, API, developer tools, platform, SaaS, vertical, moat, network effect

### Emerging
robotics, embodied, world model, synthetic data, code generation, autonomous, multimodal

## Founder relevance lens

When preparing a digest for a founder, prioritize:

1. **"Can I build on this?"** — new models, tools, APIs, infra that enable products
2. **"Does this change the market?"** — new funding, launches, acquisitions, strategic moves
3. **"Should I know about this?"** — paradigm shifts, regulatory changes, talent moves
4. **"Is this a threat or opportunity?"** — competitors, adjacent space movements

De-prioritize: pure theory, narrow domain results, incremental academic work.
