# backend/domain_guard.py
import re
import logging
import faiss
from .vectorstore import embed_model, faiss_index, META

logger = logging.getLogger(__name__)

OUT_OF_DOMAIN_SIMILARITY_THRESHOLD = 0.32

GREETINGS = {
    "hi", "hello", "hey", "namaste", "sat sri akal", "good morning",
    "good evening", "good afternoon", "salam", "who are you", "help",
    "kidan", "kidaan", "sasrikal", "namaskar"
}

COLLEGE_KEYWORDS = {
    "gndec", "gne", "college", "clg", "campus", "hostel", "mess", "fee", "fees", "admission",
    "admissions", "exam", "exams", "roll", "rollno", "result", "results", "syllabus", "scheme",
    "faculty", "teacher", "teachers", "professor", "prof", "hod", "principal", "director",
    "placement", "placements", "tnp", "package", "company", "branch", "cse", "ece", "civil",
    "mech", "mechanical", "it", "electrical", "ee", "production", "pe", "btech", "mtech",
    "bca", "mca", "mba", "bvoc", "barch", "phd", "semester", "sem", "attendance", "holiday",
    "holidays", "timing", "bus", "library", "sports", "canteen", "scholarship", "pms", "tfw",
    "sc/st", "reappear", "backlog", "degree", "ptu", "ikgptu", "curriculum", "credits",
    "kado", "kinni", "kithe", "dakhla", "admit", "form", "contact", "email", "phone",
    "address", "location", "uniform", "dress", "gurdwara", "punjabi", "hindi", "course", "courses"
}

OOD_PATTERNS = [
    r"\b(prime minister|president of|capital of|weather in|crypto|bitcoin|stock market|ipl score|cricket score)\b",
    r"\b(write|create|implement|debug|code|generate)\b.*?\b(program|script|code|algorithm|function|class|method|loop|quicksort|sorting|sql|html|css|javascript|python|c\+\+|java|cpp)\b",
    r"\b(solve the equation|math problem|differentiate|integrate|calculate derivative)\b",
    r"\b(movie review|recipe for|lyrics of|translate to french|who won the match)\b"
]
OOD_REGEX = re.compile("|".join(OOD_PATTERNS), flags=re.IGNORECASE)


def is_out_of_domain(query: str) -> bool:
    """
    Returns True if the query is strictly out of domain (unrelated to GNDEC).
    Uses a hybrid approach:
    1. Conversational greetings allow-list
    2. Explicit non-college intent reject-list
    3. College terminology allow-list (multilingual/slang aware)
    4. FAISS dense semantic similarity threshold fallback
    """
    if not query or not query.strip():
        return False

    q_lower = query.lower().strip()

    # 1. Greetings / conversational starters
    if any(q_lower == g or q_lower.startswith(g + " ") for g in GREETINGS):
        return False

    # 2. Definite out-of-domain patterns (coding, global politics, recipes)
    if OOD_REGEX.search(q_lower):
        logger.info(f"[DOMAIN GUARD] query={query!r} matched explicit out-of-domain pattern.")
        return True

    # 3. Explicit college domain terms / regional college terms
    tokens = set(re.findall(r"[a-zA-Z0-9]+", q_lower))
    if any(k in tokens or k in q_lower for k in COLLEGE_KEYWORDS):
        return False

    # 4. Dense semantic similarity fallback
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
