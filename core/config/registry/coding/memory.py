from __future__ import annotations

from typing import Any, Dict

REGISTRY: Dict[str, Dict[str, Any]] = {
    "MEMORY_EMBEDDING": {
        "model": "perplexity/pplx-embed-v1-0.6b",
        "role": "Memory Embedding",
        "reason": "Sinh embedding cho GraphRAG hybrid, summary cards, archives va artifact retrieval.",
        "tier": "MEMORY",
        "priority": 0,
        "max_tokens": 32000,
        "temperature": 0.0,
        "top_p": 1.0,
        "provider": "openrouter",
        "endpoint": "embeddings",
        "dimensions": 1024,
        "cache_enabled": True,
        "cache_ttl_seconds": 0,
    },
    "MEMORY_RERANKER": {
        "model": "cohere/rerank-4-pro",
        "role": "Memory Reranker",
        "reason": "Rerank GraphRAG hybrid candidates for important code, technical analysis, and complex memory queries.",
        "tier": "MEMORY",
        "priority": 0,
        "max_tokens": 32000,
        "temperature": 0.0,
        "top_p": 1.0,
        "provider": "openrouter",
        "endpoint": "rerank",
        "enabled": "auto",
        "candidate_limit": 50,
        "max_candidate_limit": 80,
        "top_n": 12,
        "cache_enabled": True,
        "cache_ttl_seconds": 0,
    },
}
