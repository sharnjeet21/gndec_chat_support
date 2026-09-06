# backend/domain_guard.py
import re
import logging
import faiss
from .vectorstore import embed_model, faiss_index, META

logger = logging.getLogger(__name__)

OUT_OF_DOMAIN_SIMILARITY_THRESHOLD = 0.38

GREETINGS = {
    "hi", "hello", "hey", "namaste", "sat sri akal", "good morning",
    "good evening", "good afternoon", "salam", "who are you", "help",
    "kidan", "kidaan", "sasrikal", "namaskar"
}

GNDEC_KEYWORDS = {
    "gndec", "gne", "guru nanak dev engineering", "gndec.ac.in", "gne ludhiana", "gndec ludhiana"
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

# Gurmukhi / Devanagari college terms — checked as substrings since the ASCII
# tokenizer in step 3 extracts nothing from non-Latin scripts.
NON_LATIN_COLLEGE_KEYWORDS = {
    # Gurmukhi
    "ਕਾਲਜ", "ਕਾਲਿਜ", "ਦਾਖਲਾ", "ਦਾਖ਼ਲਾ", "ਯੋਗਤਾ", "ਫੀਸ", "ਫ਼ੀਸ", "ਹੋਸਟਲ", "ਪ੍ਰੋਗਰਾਮ",
    "ਕੋਰਸ", "ਫੈਕਲਟੀ", "ਪ੍ਰੋਫੈਸਰ", "ਪਲੇਸਮੈਂਟ", "ਪ੍ਰੀਖਿਆ", "ਨਤੀਜਾ", "ਸਕਾਲਰਸ਼ਿਪ",
    # Devanagari
    "कॉलेज", "कालेज", "दाखला", "दाखिला", "प्रवेश", "योग्यता", "फीस", "फ़ीस", "हॉस्टल",
    "प्रोग्राम", "कोर्स", "फैकल्टी", "प्रोफेसर", "प्लेसमेंट", "परीक्षा", "नतीजा", "छात्रवृत्ति",
}

EXTERNAL_INSTITUTIONS_PATTERNS = [
    r"\b(iit|iits|nit|nits|iiit|iiits|bits|bits pilani|tiet|lpu|lovely professional|cu gharuan|chandigarh university|cgc|cgc landran|cgc jhanjeri|sliet|mrsptu|panjab university|pu chd|delhi university|du|jnu|bhu|amu|dtu|nsut|pec|pec chandigarh|iim|aiims|harvard|mit|stanford|oxford|cambridge)\b",
    r"\b(thapar\s+(?:university|institute|college|patiala|tiet|campus|admission|cutoff|fees?|placements?)|chitkara\s+(?:university|campus|admission|cutoff|fees?)|amity\s+(?:university|campus|admission|cutoff|fees?))\b",
    r"\b(iit\s+(bombay|delhi|madras|kanpur|kharagpur|roorkee|guwahati|hyderabad|indore|varanasi|ropar|patna|gandhinagar|bhubaneswar))\b",
    r"\b(nit\s+(jalandhar|kurukshetra|trichy|surathkal|warangal|calicut|rourkela|silchar|hamirpur|durgapur))\b",
]
EXTERNAL_INSTITUTION_REGEX = re.compile("|".join(EXTERNAL_INSTITUTIONS_PATTERNS), flags=re.IGNORECASE)
GNDEC_REGEX = re.compile(r"\b(gndec|gne|guru nanak dev engineering college|guru nanak dev engg college|here|our college)\b", flags=re.IGNORECASE)

OOD_PATTERNS = [
    r"\b(prime minister|president of|capital of|capital city|weather in|crypto|bitcoin|stock market|ipl score|cricket score|olympics|fifa world cup)\b",
    r"\b(write|create|implement|debug|code|generate|give me|show me)\b.*?\b(program|script|code|algorithm|function|class|method|loop|quicksort|sorting|binary search|bubble sort|merge sort|linked list|binary tree|stack|queue|sql query|html|css|javascript|python|c\+\+|java|cpp)\b",
    r"\b(solve the equation|math problem|differentiate|integrate|calculate derivative|theory of relativity|albert einstein|quantum mechanics|quantum entanglement|quantum computing|speed of light|black hole|photosynthesis|mitochondria|gravitation|thermodynamics|nuclear fission|periodic table)\b",
    r"\b(movie review|recipe for|lyrics of|translate to french|translate to spanish|who won the match|write an essay|tell me a joke|tell me a story)\b"
]
OOD_REGEX = re.compile("|".join(OOD_PATTERNS), flags=re.IGNORECASE)


def is_out_of_domain(query: str) -> bool:
    """
    Returns True if the query is strictly out of domain (unrelated to GNDEC).
    Uses a hybrid approach:
    1. Conversational greetings allow-list
    2. Explicit non-college intent reject-list (coding, external institutions)
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

    # 2b. External institutions without GNDEC context
    if EXTERNAL_INSTITUTION_REGEX.search(q_lower) and not GNDEC_REGEX.search(q_lower):
        logger.info(f"[DOMAIN GUARD] query={query!r} matched external institution without GNDEC context.")
        return True

    # 3. Explicit college domain terms / regional college terms
    tokens = set(re.findall(r"[a-zA-Z0-9]+", q_lower))
    if any(k in tokens for k in COLLEGE_KEYWORDS) or any((" " in k or "-" in k) and k in q_lower for k in COLLEGE_KEYWORDS):
        return False

    # 3b. Non-Latin (Gurmukhi/Devanagari) college terms — substring match
    if any(k in query for k in NON_LATIN_COLLEGE_KEYWORDS):
        return False

    # 4. Dense semantic similarity fallback (faiss_index is IndexFlatIP -> Inner Product = Cosine Similarity)
    vec = embed_model.encode([query], convert_to_numpy=True).astype("float32")
    faiss.normalize_L2(vec)
    scores, ids = faiss_index.search(vec, 1)

    cosine_sim = float(scores[0][0])
    idx = int(ids[0][0])

    if idx >= 0 and idx < len(META):
        nearest_q = META[idx].get("question", "")
        blocked = cosine_sim < OUT_OF_DOMAIN_SIMILARITY_THRESHOLD
        logger.info(
            f"[DOMAIN GUARD] query={query!r} | "
            f"nearest={nearest_q!r} | "
            f"Cosine={cosine_sim:.4f} | "
            f"threshold={OUT_OF_DOMAIN_SIMILARITY_THRESHOLD} | "
            f"blocked={blocked}"
        )
        return blocked
    else:
        logger.info(f"[DOMAIN GUARD] query={query!r} | no neighbor found | blocked=True")
        return True
