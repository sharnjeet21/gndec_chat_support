import logging
import faiss
from .vectorstore import embed_model, faiss_index, META

logger = logging.getLogger(__name__)
OUT_OF_DOMAIN_SIMILARITY_THRESHOLD = 0.40

def is_out_of_domain(query: str) -> bool:
    """
    Returns True if the query is too dissimilar to anything
    in the GNDEC knowledge base.
    """
    vec = embed_model.encode([query], convert_to_numpy=True).astype("float32")
    faiss.normalize_L2(vec)
    scores, ids = faiss_index.search(vec, 1)

    l2_score = float(scores[0][0])
    cosine_sim = max(-1.0, min(1.0, 1.0 - (l2_score ** 2) / 2.0))
    idx = int(ids[0][0])

    if idx >= 0 and idx < len(META):
        nearest_q = META[idx].get("question", "")
        blocked = cosine_sim < OUT_OF_DOMAIN_SIMILARITY_THRESHOLD
        logger.info(
            f"[DOMAIN GUARD] query={query!r} | "
            f"nearest={nearest_q!r} | "
            f"L2={l2_score:.4f} | Cosine={cosine_sim:.4f} | "
            f"threshold={OUT_OF_DOMAIN_SIMILARITY_THRESHOLD} | "
            f"blocked={blocked}"
        )
        return blocked
    else:
        logger.info(f"[DOMAIN GUARD] query={query!r} | no neighbor found | blocked=True")
        return True
