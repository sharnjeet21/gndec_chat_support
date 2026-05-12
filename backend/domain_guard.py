# backend/domain_guard.py
"""
Domain Guard — GNDEC Edition
=============================
Rejects questions that are too far from the GNDEC knowledge base
using FAISS L2 distance on the embedded query.

Threshold tuning:
  - Lower value  → stricter (more questions rejected)
  - Higher value → looser  (more questions allowed through)

With the GNDEC dataset (465 Q&A pairs), 1.6 is a good starting point.
Raise to 1.9 if too many valid questions are being blocked.
"""

import logging

from .vectorstore import embed_model, faiss_index, META

logger = logging.getLogger(__name__)

# FAISS IndexFlatL2: lower score = more similar
# Tuned for GNDEC dataset — adjust if needed
OUT_OF_DOMAIN_THRESHOLD = 1.6


def is_out_of_domain(query: str) -> bool:
    """
    Returns True if the query is too dissimilar to anything
    in the GNDEC knowledge base.
    """
    vec = embed_model.encode([query], convert_to_numpy=True).astype("float32")
    scores, ids = faiss_index.search(vec, 1)

    score = float(scores[0][0])
    idx   = int(ids[0][0])

    if idx >= 0 and idx < len(META):
        nearest_q = META[idx].get("question", "")
        logger.info(
            f"[DOMAIN GUARD] query={query!r} | "
            f"nearest={nearest_q!r} | "
            f"L2={score:.4f} | "
            f"threshold={OUT_OF_DOMAIN_THRESHOLD} | "
            f"blocked={score > OUT_OF_DOMAIN_THRESHOLD}"
        )
    else:
        logger.info(f"[DOMAIN GUARD] query={query!r} | no neighbor found | blocked=True")
        return True

    return score > OUT_OF_DOMAIN_THRESHOLD
