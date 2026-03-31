"""Taxonomy-based classifier for Earlybird items.

Provides a predefined hierarchical taxonomy of AI-related categories and
subcategories, along with keyword-based classification logic.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from earlybird.models import Item


# ── Taxonomy ────────────────────────────────────────────────────────────────

TAXONOMY: dict[str, dict] = {
    "AI Research": {
        "color": "#2563eb",
        "subcategories": {
            "NLP & Language Models": {
                "keywords": [
                    "language model", "LLM", "GPT", "transformer", "NLP",
                    "text generation", "tokenizer", "BERT", "attention mechanism",
                    "prompt", "chat", "dialogue", "translation", "summarization",
                    "sentiment", "fine-tuning", "RLHF", "instruction", "alignment",
                    "hallucination", "context window",
                ],
            },
            "Computer Vision": {
                "keywords": [
                    "vision", "image", "object detection", "segmentation",
                    "diffusion", "GAN", "VAE", "stable diffusion",
                    "image generation", "video", "3D", "point cloud", "OCR",
                    "face", "pose estimation", "depth",
                ],
            },
            "Multimodal": {
                "keywords": [
                    "multimodal", "vision-language", "VLM", "image-text", "CLIP",
                    "visual question", "audio", "speech", "TTS", "ASR", "voice",
                ],
            },
            "Reasoning & Agents": {
                "keywords": [
                    "reasoning", "chain-of-thought", "agent", "planning",
                    "tool use", "code generation", "math", "logic", "benchmark",
                    "evaluation", "self-play", "reflection", "CoT", "o1", "o3",
                ],
            },
            "Training & Infrastructure": {
                "keywords": [
                    "training", "distributed", "GPU", "TPU", "CUDA", "inference",
                    "serving", "optimization", "quantization", "distillation",
                    "pruning", "MoE", "mixture of experts", "scaling",
                    "efficiency", "memory", "throughput", "latency", "batch",
                    "parallelism", "FSDP", "DeepSpeed",
                ],
            },
            "Retrieval & Knowledge": {
                "keywords": [
                    "RAG", "retrieval", "embedding", "vector", "knowledge graph",
                    "search", "index", "database", "semantic search", "reranking",
                ],
            },
            "Reinforcement Learning": {
                "keywords": [
                    "reinforcement learning", "RL", "reward", "policy", "PPO",
                    "DPO", "environment", "simulation", "game", "control",
                ],
            },
        },
    },
    "Data & ML Ops": {
        "color": "#0891b2",
        "subcategories": {
            "Datasets & Benchmarks": {
                "keywords": [
                    "dataset", "benchmark", "evaluation", "leaderboard",
                    "annotation", "synthetic data", "data quality",
                    "data curation", "corpus",
                ],
            },
            "ML Ops & Tools": {
                "keywords": [
                    "MLOps", "pipeline", "deployment", "monitoring", "experiment",
                    "tracking", "model registry", "CI/CD", "Docker", "Kubernetes",
                    "API", "SDK", "framework", "library", "open source",
                ],
            },
        },
    },
    "Hardware & Robotics": {
        "color": "#7c3aed",
        "subcategories": {
            "Chips & Accelerators": {
                "keywords": [
                    "chip", "GPU", "TPU", "NPU", "ASIC", "FPGA", "silicon",
                    "semiconductor", "NVIDIA", "AMD", "Intel", "Apple", "Groq",
                ],
            },
            "Robotics & Embodied AI": {
                "keywords": [
                    "robot", "robotics", "embodied", "manipulation", "navigation",
                    "autonomous", "drone", "self-driving", "humanoid", "sensor",
                ],
            },
        },
    },
    "Funding & Startups": {
        "color": "#059669",
        "subcategories": {
            "Funding Rounds": {
                "keywords": [
                    "funding", "Series A", "Series B", "Series C", "seed",
                    "raise", "million", "billion", "valuation", "investor",
                    "venture", "VC", "capital", "investment",
                ],
            },
            "Startup Launches": {
                "keywords": [
                    "launch", "startup", "YC", "Y Combinator", "founded",
                    "co-founder", "CEO", "CTO", "pivot", "product-market fit",
                ],
            },
            "Market & Business": {
                "keywords": [
                    "market", "revenue", "growth", "enterprise", "SaaS", "B2B",
                    "platform", "pricing", "ARR", "IPO", "acquisition", "merger",
                ],
            },
        },
    },
    "Industry & News": {
        "color": "#dc2626",
        "subcategories": {
            "Company News": {
                "keywords": [
                    "Google", "Meta", "OpenAI", "Anthropic", "Microsoft",
                    "Amazon", "Apple", "DeepMind", "Mistral", "xAI", "Cohere",
                    "Stability", "announce", "release", "update", "partnership",
                ],
            },
            "Policy & Ethics": {
                "keywords": [
                    "regulation", "policy", "ethics", "safety", "bias",
                    "fairness", "privacy", "copyright", "law", "governance",
                    "EU", "AI Act",
                ],
            },
            "Trends & Analysis": {
                "keywords": [
                    "trend", "analysis", "report", "survey", "state of",
                    "outlook", "prediction", "forecast", "review",
                    "retrospective",
                ],
            },
        },
    },
    "Science & Math": {
        "color": "#d97706",
        "subcategories": {
            "Mathematics": {
                "keywords": [
                    "mathematics", "theorem", "proof", "algebra", "topology",
                    "optimization", "convex", "gradient", "convergence",
                    "stochastic",
                ],
            },
            "Scientific ML": {
                "keywords": [
                    "scientific", "physics", "biology", "chemistry", "protein",
                    "drug", "molecule", "materials", "climate", "weather",
                    "medical", "healthcare", "genomics", "AlphaFold",
                ],
            },
        },
    },
    "Media & Content": {
        "color": "#db2777",
        "subcategories": {
            "Podcasts & Talks": {
                "keywords": [
                    "podcast", "episode", "interview", "talk", "keynote",
                    "conversation", "discussion",
                ],
            },
            "Newsletters & Blogs": {
                "keywords": [
                    "newsletter", "blog", "post", "article", "essay", "opinion",
                    "weekly", "digest", "roundup",
                ],
            },
        },
    },
}

# Keywords that are short or are common English words need word-boundary
# matching to avoid false positives.  We consider anything <= 3 chars or
# in an explicit set as requiring boundaries.
_SHORT_KEYWORD_MAX_LEN = 3
_BOUNDARY_KEYWORDS: set[str] = {
    "face", "game", "depth", "post", "law", "drug", "math", "chat",
    "voice", "image", "video", "raise", "seed", "launch", "growth",
    "release", "update", "report", "review", "proof", "control",
    "search", "index", "batch", "agent", "policy", "reward",
}


# ── Precompiled regex patterns ──────────────────────────────────────────────

def _build_pattern(keyword: str) -> re.Pattern[str]:
    """Build a compiled regex for a keyword.

    Short keywords (<=3 chars) and select common words use word-boundary
    matching (``\\b``) to avoid false positives.  Longer, more specific
    phrases use simple substring matching via ``re.search``.
    """
    escaped = re.escape(keyword)
    if len(keyword) <= _SHORT_KEYWORD_MAX_LEN or keyword.lower() in _BOUNDARY_KEYWORDS:
        return re.compile(rf"\b{escaped}\b", re.IGNORECASE)
    return re.compile(escaped, re.IGNORECASE)


# Pre-build patterns once at import time for every keyword in the taxonomy.
_PATTERNS: dict[str, dict[str, list[tuple[str, re.Pattern[str]]]]] = {}
for _cat, _cat_info in TAXONOMY.items():
    _PATTERNS[_cat] = {}
    for _sub, _sub_info in _cat_info["subcategories"].items():
        _PATTERNS[_cat][_sub] = [
            (kw, _build_pattern(kw)) for kw in _sub_info["keywords"]
        ]


# ── Source-based heuristics ─────────────────────────────────────────────────

_NEWSLETTER_SOURCES: set[str] = {"the_batch", "import_ai", "interconnects"}

_SOURCE_FALLBACKS: dict[str, tuple[str, str]] = {
    "arxiv": ("AI Research", "NLP & Language Models"),
    "huggingface_papers": ("AI Research", "NLP & Language Models"),
    "hf_papers": ("AI Research", "NLP & Language Models"),
    "huggingface_trending": ("Data & ML Ops", "ML Ops & Tools"),
    "hf_trending_models": ("Data & ML Ops", "ML Ops & Tools"),
    "hf_trending_spaces": ("Data & ML Ops", "ML Ops & Tools"),
    "crunchbase": ("Funding & Startups", "Funding Rounds"),
    "yc_launches": ("Funding & Startups", "Startup Launches"),
    "nfx": ("Funding & Startups", "Market & Business"),
}

_DEFAULT_FALLBACK: tuple[str, str] = ("Industry & News", "Trends & Analysis")


# ── Public API ──────────────────────────────────────────────────────────────

def classify_item(item: Item) -> tuple[str, str]:
    """Classify an item into ``(category, subcategory)`` using keyword matching.

    The function combines *title*, *abstract*, and *source* into a single
    text blob and scores every subcategory by the number of distinct keyword
    matches.  The subcategory with the highest score wins.

    When no keyword matches are found, source-based heuristics are applied
    as a fallback.  The ultimate default is ``("Industry & News", "Trends &
    Analysis")``.
    """
    text = " ".join(filter(None, [item.title, item.abstract, item.source]))

    best_score = 0
    best_cat = ""
    best_sub = ""

    for cat, subs in _PATTERNS.items():
        for sub, patterns in subs.items():
            score = sum(1 for _kw, pat in patterns if pat.search(text))
            if score > best_score:
                best_score = score
                best_cat = cat
                best_sub = sub

    if best_score > 0:
        return best_cat, best_sub

    # -- Source-based fallbacks ------------------------------------------------
    source = item.source.lower() if item.source else ""

    # Exact source lookup
    if item.source in _SOURCE_FALLBACKS:
        return _SOURCE_FALLBACKS[item.source]

    # Hackernews: already tried keyword match above, fall back to Industry & News
    if source == "hackernews":
        return "Industry & News", "Company News"

    # Podcast sources
    if "podcast" in source:
        return "Media & Content", "Podcasts & Talks"

    # Newsletter sources
    if "newsletter" in source or item.source in _NEWSLETTER_SOURCES:
        return "Media & Content", "Newsletters & Blogs"

    return _DEFAULT_FALLBACK


def classify_all(items: list[Item]) -> list[tuple[str, str]]:
    """Classify a list of items, returning ``[(category, subcategory), ...]``."""
    return [classify_item(item) for item in items]


def get_taxonomy() -> dict:
    """Return the full taxonomy dictionary."""
    return TAXONOMY


def get_category_color(category: str) -> str:
    """Return the hex color string for *category*, or ``"#999999"`` if unknown."""
    info = TAXONOMY.get(category)
    if info is not None:
        return info["color"]
    return "#999999"


# ── Source colors (for territory grouping by data source) ─────────────────

SOURCE_COLORS: dict[str, str] = {
    "arxiv": "#e74c3c",              # red
    "huggingface_papers": "#3498db", # blue
    "hf_papers": "#3498db",          # blue
    "huggingface_trending": "#9b59b6", # purple
    "hackernews": "#ff6600",         # orange
    "crunchbase": "#2ecc71",         # green
    "yc_launches": "#8e44ad",        # deep purple
    "github_trending": "#f1c40f",    # yellow
    "pwc": "#e67e22",                # dark orange
    "import_ai": "#1abc9c",          # turquoise
    "interconnects": "#16a085",      # dark teal
    "the_batch": "#d35400",          # pumpkin
    "latent_space": "#c0392b",       # dark red
    "lex_fridman": "#27ae60",        # emerald
    "nfx": "#2980b9",               # belize blue
    "acquired": "#f39c12",           # sunflower
}
DEFAULT_SOURCE_COLOR = "#95a5a6"     # grey


def get_source_color(source: str) -> str:
    """Return the hex color string for a data *source*, or grey if unknown."""
    return SOURCE_COLORS.get(source, DEFAULT_SOURCE_COLOR)


def get_all_categories() -> list[str]:
    """Return a list of all top-level category names."""
    return list(TAXONOMY.keys())


def get_subcategories(category: str) -> list[str]:
    """Return subcategory names for *category*, or an empty list if unknown."""
    info = TAXONOMY.get(category)
    if info is None:
        return []
    return list(info["subcategories"].keys())
