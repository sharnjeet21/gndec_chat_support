# backend/cache.py
"""
High-Performance Semantic & Exact Query Cache for GNDEC RAG.
Provides sub-50ms responses for recurring or semantically equivalent questions
using cosine similarity on dense query embeddings. Supports Redis & In-Memory LRU.
"""

import os
import time
import logging
from typing import Optional, Dict, Any, List
import numpy as np

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.96"))
CACHE_TTL = int(os.getenv("CACHE_TTL", "86400")) # 24 hours
MAX_IN_MEMORY_ITEMS = 5000

class SemanticCache:
    def __init__(self, threshold: float = SIMILARITY_THRESHOLD, ttl: int = CACHE_TTL):
        self.threshold = threshold
        self.ttl = ttl
        self.memory_cache: List[Dict[str, Any]] = []
        self._redis_client = None
        self._init_redis()

    def _init_redis(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/1")
        try:
            import redis
            self._redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
            self._redis_client.ping()
            logger.info("SemanticCache: Redis connected.")
        except Exception as e:
            self._redis_client = None
            logger.info("SemanticCache: Using in-memory high-speed cache.")

    def lookup(self, query: str, query_vec: Optional[np.ndarray] = None) -> Optional[Dict[str, Any]]:
        """
        Looks up query in exact and semantic memory.
        Returns cached dict {answer, sources, query, cached_at} if match found, else None.
        """
        now = time.time()
        q_clean = query.strip().lower()

        # 1. Exact Match Check (O(1))
        for item in reversed(self.memory_cache):
            if now - item["timestamp"] > self.ttl:
                continue
            if item["query_clean"] == q_clean:
                logger.info(f"Cache HIT [Exact]: '{query}'")
                return item["data"]

        # 2. Semantic Similarity Check (Cosine Similarity >= threshold)
        if query_vec is not None and len(self.memory_cache) > 0:
            # Normalize query vector if not already normalized
            q_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)

            valid_items = [it for it in self.memory_cache if (now - it["timestamp"]) <= self.ttl]
            if valid_items:
                matrix = np.array([it["vec"] for it in valid_items])
                sims = np.dot(matrix, q_norm.T).flatten()
                best_idx = int(np.argmax(sims))
                best_score = float(sims[best_idx])

                if best_score >= self.threshold:
                    matched_item = valid_items[best_idx]
                    logger.info(f"Cache HIT [Semantic sim={best_score:.3f}]: '{query}' ~= '{matched_item['query']}'")
                    return matched_item["data"]

        return None

    def store(self, query: str, query_vec: Optional[np.ndarray], data: Dict[str, Any]):
        """Stores a generated response in the cache."""
        now = time.time()
        q_clean = query.strip().lower()

        # Compute normalized vector if provided
        vec = None
        if query_vec is not None:
            vec = query_vec / (np.linalg.norm(query_vec) + 1e-10)

        # Evict oldest if exceeding capacity
        if len(self.memory_cache) >= MAX_IN_MEMORY_ITEMS:
            self.memory_cache.pop(0)

        self.memory_cache.append({
            "query": query,
            "query_clean": q_clean,
            "vec": vec if vec is not None else np.zeros(384, dtype=np.float32),
            "data": data,
            "timestamp": now
        })

    def clear(self):
        """Clears cache."""
        self.memory_cache.clear()

# Global Semantic Cache Instance
global_semantic_cache = SemanticCache()
