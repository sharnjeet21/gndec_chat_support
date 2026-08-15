import logging
from .vectorstore import embed_model, faiss_index, META

logger = logging.getLogger(__name__)
OUT_OF_DOMAIN_THRESHOLD = 1.2

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
