from __future__ import annotations

import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
DATA_DIR = Path(os.environ.get("EARLYBIRD_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── HTTP ─────────────────────────────────────────────────────────────────────
USER_AGENT = "earlybird/0.1 (content-radar)"
HTTP_TIMEOUT = 30  # seconds

# ── API keys (optional) ─────────────────────────────────────────────────────
HF_TOKEN: str | None = os.environ.get("HF_TOKEN")
SEMANTIC_SCHOLAR_KEY: str | None = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")

# ── Hacker News ──────────────────────────────────────────────────────────────
HN_MIN_POINTS = 100

# ── HF Papers ────────────────────────────────────────────────────────────────
HF_PAPERS_MIN_UPVOTES = 5

# ── Source groups (used by CLI --sources flag) ───────────────────────────────
SOURCE_GROUPS: dict[str, list[str]] = {
    "arxiv": ["arxiv"],
    "hf_papers": ["hf_papers"],
    "hf_trending": ["hf_trending_models", "hf_trending_spaces"],
    "pwc": ["pwc"],
    "hn": ["hackernews"],
    "venture": ["crunchbase", "yc_launches", "nfx"],
    "newsletters": ["the_batch", "import_ai", "interconnects"],
    "podcasts": ["latent_space", "lex_fridman", "acquired"],
    "all": [],  # filled at import time
}
# "all" = union of every source
_all_sources: list[str] = []
for _group, _members in SOURCE_GROUPS.items():
    if _group != "all":
        _all_sources.extend(_members)
SOURCE_GROUPS["all"] = _all_sources

# ── Keyword pre-filter ───────────────────────────────────────────────────────
KEYWORDS: list[str] = [
    # Core AI
    "LLM", "transformer", "attention", "GPT", "language model",
    "foundation model", "fine-tuning", "RLHF", "alignment",
    "inference", "training", "benchmark", "evaluation",
    # Architecture & methods
    "diffusion", "GAN", "VAE", "reinforcement learning",
    "multi-modal", "vision-language", "embedding", "retrieval",
    "RAG", "agent", "chain-of-thought", "reasoning",
    "mixture of experts", "MoE", "distillation", "quantization",
    # Infrastructure
    "GPU", "TPU", "CUDA", "distributed training", "serving",
    "latency", "throughput", "scaling", "infrastructure",
    # Product & business
    "startup", "funding", "Series A", "Series B", "YC",
    "open source", "API", "developer tools", "platform",
    "SaaS", "vertical", "moat", "network effect",
    # Emerging
    "robotics", "embodied", "world model", "synthetic data",
    "code generation", "autonomous", "multimodal",
]

# ── Backfill ────────────────────────────────────────────────────────────────
BACKFILL_DIR = DATA_DIR / "backfill"
BACKFILL_DIR.mkdir(parents=True, exist_ok=True)

# ── Map pipeline ────────────────────────────────────────────────────────────
MAP_DIR = DATA_DIR / "map"
MAP_DIR.mkdir(parents=True, exist_ok=True)
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
UMAP_N_NEIGHBORS = 30
UMAP_MIN_DIST = 0.3
LEIDEN_RESOLUTION = 0.8
KNN_K = 15
KNN_THRESHOLD = 0.3

# Cluster colors (20 distinct colors for up to 20 clusters)
CLUSTER_COLORS = [
    "#4a90d9", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6",
    "#1abc9c", "#e67e22", "#3498db", "#e91e63", "#00bcd4",
    "#ff5722", "#8bc34a", "#673ab7", "#ff9800", "#009688",
    "#795548", "#607d8b", "#cddc39", "#ffc107", "#03a9f4",
]

# ── Inter-cluster connections ───────────────────────────────────────────────
CONNECTION_THRESHOLD = 0.4
CONNECTION_MAX_EDGES = 30
CONNECTION_CURVATURE = 0.2

# ── Sub-topic labels ───────────────────────────────────────────────────────
SUB_CLUSTERS_PER_CLUSTER = 3
SUB_LABEL_MIN_ITEMS = 6

# ── Lex Fridman episode filter keywords ──────────────────────────────────────
LEX_KEYWORDS: list[str] = [
    "AI", "machine learning", "deep learning", "neural", "GPT", "LLM",
    "CEO", "CTO", "founder", "startup",
    "Google", "Meta", "OpenAI", "Anthropic", "DeepMind",
    "computer science", "robotics", "AGI",
]

# ── Crunchbase AI filter keywords ────────────────────────────────────────────
CRUNCHBASE_KEYWORDS: list[str] = [
    "AI", "artificial intelligence", "machine learning", "LLM",
    "foundation model", "generative AI",
]
