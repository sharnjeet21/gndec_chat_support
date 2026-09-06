# backend/vectorstore.py
import os
import re
import json
import faiss
import logging
import torch
from typing import List, Dict, Any, Tuple

# Restrict torch threads for predictable CPU latency
torch.set_num_threads(2)

from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder
from langchain_core.documents import Document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(HERE), "data")
FAISS_DIR = os.path.join(HERE, "faiss_store")
INDEX_PATH = os.path.join(FAISS_DIR, "faq.index")
META_PATH = os.path.join(FAISS_DIR, "meta.json")
FACULTY_PATH = os.path.join(DATA_DIR, "faculty.json")
FEE_PATH = os.path.join(DATA_DIR, "fee_structures.json")

if not os.path.exists(INDEX_PATH) or not os.path.exists(META_PATH):
    raise RuntimeError(
        f"FAISS index or meta.json missing!\nRun: python backend/build_vector_db.py"
    )

logger.info("🔄 Loading FAISS index & metadata...")
faiss_index = faiss.read_index(INDEX_PATH)

with open(META_PATH, "r", encoding="utf-8") as f:
    META: List[Dict[str, Any]] = json.load(f)

# Load and merge any curated/external datasets
EXTERNAL_PATH = os.path.join(DATA_DIR, "external_facts.json")
COURSES_PATH = os.path.join(DATA_DIR, "courses_offered.json")

seen_qs = {m.get("question", "").strip().lower() for m in META}
for extra_path in [EXTERNAL_PATH, COURSES_PATH, FEE_PATH]:
    if os.path.exists(extra_path):
        try:
            with open(extra_path, "r", encoding="utf-8") as f:
                extra_data = json.load(f)
                for item in extra_data:
                    q = item.get("question", "").strip()
                    if q and q.lower() not in seen_qs:
                        META.append(item)
                        seen_qs.add(q.lower())
        except Exception as e:
            logger.warning(f"Could not load {extra_path}: {e}")

# Structured Faculty Data
FACULTY_LIST: List[Dict[str, Any]] = []
if os.path.exists(FACULTY_PATH):
    try:
        with open(FACULTY_PATH, "r", encoding="utf-8") as f:
            FACULTY_LIST = json.load(f)
        logger.info(f"Loaded {len(FACULTY_LIST)} faculty members for structured lookup.")
    except Exception as e:
        logger.warning(f"Could not load faculty.json: {e}")

# Structured Fee Structure Data
FEE_LIST: List[Dict[str, Any]] = []
if os.path.exists(FEE_PATH):
    try:
        with open(FEE_PATH, "r", encoding="utf-8") as f:
            FEE_LIST = json.load(f)
        logger.info(f"Loaded {len(FEE_LIST)} fee structure records for structured lookup.")
    except Exception as e:
        logger.warning(f"Could not load fee_structures.json: {e}")

# Structured Courses Offered Data — verified 7 B.Tech branches, loaded with is_aggregate flag
COURSES_LIST: List[Dict[str, Any]] = []
if os.path.exists(COURSES_PATH):
    try:
        with open(COURSES_PATH, "r", encoding="utf-8") as f:
            raw_courses = json.load(f)
        for item in raw_courses:
            item["is_aggregate"] = True
        COURSES_LIST = raw_courses
        logger.info(f"Loaded {len(COURSES_LIST)} verified course entries for structured lookup.")
    except Exception as e:
        logger.warning(f"Could not load courses_offered.json: {e}")

# Structured Admission Process Data — verified application/entrance-exam procedures
ADMISSION_PATH = os.path.join(DATA_DIR, "admission_process.json")
ADMISSION_LIST: List[Dict[str, Any]] = []
if os.path.exists(ADMISSION_PATH):
    try:
        with open(ADMISSION_PATH, "r", encoding="utf-8") as f:
            raw_admission = json.load(f)
        for item in raw_admission:
            item["is_aggregate"] = True
        ADMISSION_LIST = raw_admission
        logger.info(f"Loaded {len(ADMISSION_LIST)} verified admission-process entries for structured lookup.")
    except Exception as e:
        logger.warning(f"Could not load admission_process.json: {e}")

# Embedding Model (CPU)
MODEL_NAME = "all-MiniLM-L6-v2"
logger.info(f"Loading embedding model: {MODEL_NAME} on CPU")
embed_model = SentenceTransformer(MODEL_NAME, device="cpu")

# Cross-Encoder Re-ranker (CPU)
RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
logger.info(f"Loading Cross-Encoder reranker: {RERANKER_MODEL_NAME} on CPU")
cross_encoder = CrossEncoder(RERANKER_MODEL_NAME, device="cpu")


def encode_query(query: str):
    """Encodes query into L2-normalized dense vector for semantic search and caching."""
    vec = embed_model.encode([query], convert_to_numpy=True, show_progress_bar=False).astype("float32")
    faiss.normalize_L2(vec)
    return vec[0]


def metadata_to_doc(item: Dict[str, Any]) -> Document:
    """Convert metadata record into LangChain Document"""
    text = f"Q: {item['question']}\nA: {item['answer']}\nSection: {item.get('section', 'General')}"
    return Document(page_content=text, metadata=item)


# Lightweight tokenization for BM25
def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


logger.info("🔄 Building lightweight BM25 keyword index...")
# Index all documents including fee structures and syllabi
bm25_corpus = [_tokenize(f"{m.get('question', '')} {m.get('section', '')}") for m in META]
bm25_index = BM25Okapi(bm25_corpus)
logger.info("✅ BM25 index built successfully.")


# ----------------------------------------------------
# Structured Faculty Matcher (100% Precision Entity Lookup)
# ----------------------------------------------------
FACULTY_TITLES = {"dr", "er", "ar", "prof", "mr", "ms", "mrs"}
COMMON_NAME_TOKENS = {
    "dr", "er", "ar", "prof", "mr", "ms", "mrs", "singh", "kaur", "kumar",
    "sharma", "gndec", "the", "is", "who", "what", "email", "contact",
    "of", "in", "department", "and", "faculty", "teacher", "hod", "head"
}

DEPT_PATTERNS = {
    "Applied Science": re.compile(r"\b(applied science|applied sciences|physics|chemistry|mathematics|maths|humanities)\b", re.IGNORECASE),
    "Business Administration": re.compile(r"\b(business administration|mba|management)\b", re.IGNORECASE),
    "Civil Engineering": re.compile(r"(?i:\b(civil|civil engineering|civil\s+dept)\b)|\bCE\b"),
    "Computer Applications": re.compile(r"\b(computer applications|mca|bca)\b", re.IGNORECASE),
    "Computer Center": re.compile(r"(?i:\b(computer center|computer centre)\b)|\bCC\b"),
    "Computer Science & Engg.": re.compile(r"(?i:\b(computer science|cse|comp\s*sci)\b)|\bCS\b"),
    "Electrical Engineering": re.compile(r"(?i:\b(electrical|electrical engineering|electrical\s+dept)\b)|\bEE\b"),
    "Electronics & Communication Engineering": re.compile(r"\b(electronics|ece|electronics and communication|electronics & communication)\b", re.IGNORECASE),
    "Information Technology": re.compile(r"(?i:\b(information technology|info\s*tech|it\s+dept|it\s+department)\b)|\bIT\b"),
    "Mechanical Engineering": re.compile(r"(?i:\b(mechanical|mechanical engineering|mech|mech\s+dept)\b)|\bME\b"),
    "Production Engineering": re.compile(r"(?i:\b(production|production engineering|prod\s+engg)\b)|\bPE\b"),
    "School of Architecture": re.compile(r"\b(architecture|b\.?arch|school of architecture)\b", re.IGNORECASE),
    "Sports": re.compile(r"\b(sports|physical education|dpe)\b", re.IGNORECASE),
    "Workshops": re.compile(r"\b(workshop|workshops)\b", re.IGNORECASE),
}

PHD_PATTERNS = re.compile(r"\b(phd|ph\.d|doctorate|doctorates|doctoral)\b", re.IGNORECASE)
HOD_PATTERNS = re.compile(r"\b(hod|hods|head\s+of|heads?\s+of|department\s+heads?|dept\s+heads?|incharge|in-charge)\b", re.IGNORECASE)
ROSTER_PATTERNS = re.compile(
    r"\b(faculty|faculties|teachers?|teaches|teaching|professors?|staff|directory|roster|members?|"
    r"list of faculty|list of teachers|list of professors|who is in|who are in)\b",
    re.IGNORECASE
)

# All academic titles that imply a PhD/doctorate (covers "Professor", "Associate Professor",
# "Assistant Professor", "Instructor", "Lab. Supdt.", "DPE" — anyone with a doctoral degree)
PHD_TITLE_PATTERN = re.compile(
    r"\b(professor|associate professor|assistant professor|instructor|lab\.?\s*supdt|dpe|"
    r"professor and head|head of department|hod)\b", re.IGNORECASE
)
# Names that may lack "DR." prefix but are still doctorate holders
NON_DR_TITLES = {"ASSISTANT PROFESSOR", "ASSOCIATE PROFESSOR", "PROFESSOR", "INSTRUCTOR", "LAB. SUPDT.", "DPE"}

OFFICIAL_HOD_MAP = {
    "Computer Science & Engg.": {"name": "Dr. Kiran Jyoti", "designation": "Professor & Head", "email": "kiranjyotibains@gndec.ac.in"},
    "Information Technology": {"name": "Dr. Kulvinder Singh Mann", "designation": "Professor & Head", "email": "mannkulvinder@gndec.ac.in"},
    "Mechanical Engineering": {"name": "Dr. Harmeet Singh", "designation": "Professor & Head", "email": "hms@gndec.ac.in"},
    "Electrical Engineering": {"name": "Dr. Kanwardeep Singh", "designation": "Professor & Head", "email": "kds@gndec.ac.in"},
    "Civil Engineering": {"name": "Dr. Prashant Garg", "designation": "Professor & Head", "email": "pgarg@gndec.ac.in"},
    "Electronics & Communication Engineering": {"name": "Dr. Narwant Singh Grewal", "designation": "Professor & Head", "email": "narwant@gndec.ac.in"},
    "Applied Science": {"name": "Dr. Harpreet Kaur Grewal", "designation": "Professor & Head", "email": "hkgrewal@gndec.ac.in"},
    "Production Engineering": {"name": "Dr. Jasmaninder Singh Grewal", "designation": "Professor & Head", "email": "jsgrewal_2000@gndec.ac.in"},
    "Business Administration": {"name": "Dr. Amanjot Kaur Gill", "designation": "Associate Professor & Head", "email": "amanjot@gndec.ac.in"},
    "Computer Applications": {"name": "Dr. Jasbir Singh Saini", "designation": "Associate Professor (CP) cum System Analyst", "email": "mca@gndec.ac.in"},
    "School of Architecture": {"name": "Ar. Akanksha Sharma", "designation": "Professor & Head", "email": "hod_arch@gndec.ac.in"},
    "Workshops": {"name": "Dr. Jasmaninder Singh Grewal", "designation": "Professor & Head Workshop", "email": "jsgrewal_2000@gndec.ac.in"},
    "Computer Center": {"name": "Dr. Jasbir Singh Saini", "designation": "Associate Professor (CP) cum System Analyst", "email": "cc@gndec.ac.in"},
    "Sports": {"name": "Dr. Gunjan Bhardwaj", "designation": "DPE", "email": "gunjan@gndec.ac.in"},
}


def _format_faculty_table(members: List[Dict[str, Any]], title: str, include_dept: bool = False) -> str:
    lines = [f"### {title}\n"]
    if include_dept:
        lines.append("| Sr No. | Name | Designation | Department | Email |")
        lines.append("| :---: | :--- | :--- | :--- | :--- |")
        for i, m in enumerate(members, 1):
            lines.append(f"| {i} | {m['name']} | {m['designation']} | {m['department']} | {m['email']} |")
    else:
        lines.append("| Sr No. | Name | Designation | Email |")
        lines.append("| :---: | :--- | :--- | :--- |")
        for i, m in enumerate(members, 1):
            lines.append(f"| {i} | {m['name']} | {m['designation']} | {m['email']} |")
    return "\n".join(lines)


def find_faculty_matches(query: str) -> List[Document]:
    """Finds exact or aggregate faculty matches from structured records."""
    if not FACULTY_LIST:
        return []

    matched_dept = None
    for dept, pat in DEPT_PATTERNS.items():
        if pat.search(query):
            matched_dept = dept
            break

    # 1. PhD / Doctorate Query
    if PHD_PATTERNS.search(query):
        phd_fac = [
            m for m in FACULTY_LIST
            if m.get("name", "").upper().startswith(("DR.", "DR "))
            or "PH.D" in m.get("designation", "").upper()
            or "PHD" in m.get("designation", "").upper()
            or "PH.D" in m.get("qualification", "").upper()
            or "PHD" in m.get("qualification", "").upper()
            or "DOCTOR OF" in m.get("qualification", "").upper()
        ]
        if matched_dept:
            dept_phd = [m for m in phd_fac if m.get("department") == matched_dept]
            table_md = _format_faculty_table(dept_phd, f"PhD Faculty - {matched_dept}")
            doc_data = {
                "question": f"Which faculty members hold a PhD degree in {matched_dept} at GNDEC?",
                "answer": table_md,
                "section": f"Faculty Directory - PhD in {matched_dept}",
                "source_file": "faculty.json",
                "is_aggregate": True
            }
            return [metadata_to_doc(doc_data)]
        else:
            by_dept = {}
            for m in phd_fac:
                by_dept.setdefault(m["department"], []).append(m)

            lines = [f"Guru Nanak Dev Engineering College (GNDEC), Ludhiana has **{len(phd_fac)} PhD faculty members** across {len(by_dept)} departments:\n"]
            for d, members in sorted(by_dept.items()):
                lines.append(f"**{d}** ({len(members)}):")
                names = ", ".join(m["name"] for m in sorted(members, key=lambda x: x.get("name", "")))
                lines.append(f"  {names}")
                lines.append("")

            full_md = "\n".join(lines)
            doc_data = {
                "question": "Which faculty members hold a PhD degree at Guru Nanak Dev Engineering College (GNDEC)?",
                "answer": full_md,
                "section": "Faculty Directory - PhD Faculty",
                "source_file": "faculty.json",
                "is_aggregate": True
            }
            return [metadata_to_doc(doc_data)]

    # 2. HOD Query
    if HOD_PATTERNS.search(query):
        hods = [m for m in FACULTY_LIST if "head" in m.get("designation", "").lower() or "hod" in m.get("designation", "").lower()]
        if matched_dept:
            dept_hod = [m for m in hods if m.get("department") == matched_dept]
            h = OFFICIAL_HOD_MAP.get(matched_dept) or (dept_hod[0] if dept_hod else None)
            if h:
                ans = f"The Head of Department (HOD) of **{matched_dept}** at GNDEC is **{h['name']}** ({h['designation']}).\n- **Email:** {h['email']}"
                doc_data = {
                    "question": f"Who is the Head of Department (HOD) of {matched_dept} at GNDEC?",
                    "answer": ans,
                    "section": f"Faculty Directory - HOD {matched_dept}",
                    "source_file": "faculty.json",
                    "is_aggregate": True
                }
                return [metadata_to_doc(doc_data)]
        else:
            table_md = _format_faculty_table(hods, "Heads of Departments (HODs) - GNDEC", include_dept=True)
            doc_data = {
                "question": "Who are the Heads of Departments (HODs) at GNDEC?",
                "answer": table_md,
                "section": "Faculty Directory - HODs",
                "source_file": "faculty.json",
                "is_aggregate": True
            }
            return [metadata_to_doc(doc_data)]

    # 3. Department Roster Query
    if ROSTER_PATTERNS.search(query) and matched_dept:
        dept_fac = [m for m in FACULTY_LIST if m.get("department") == matched_dept]
        table_md = _format_faculty_table(dept_fac, f"Faculty Directory - {matched_dept}")
        doc_data = {
            "question": f"Who are the faculty members in the {matched_dept} department at GNDEC?",
            "answer": table_md,
            "section": f"Faculty Directory - {matched_dept}",
            "source_file": "faculty.json",
            "is_aggregate": True
        }
        return [metadata_to_doc(doc_data)]

    # 4. Individual Faculty Name Matcher
    q_tokens = set(re.findall(r"[a-zA-Z]+", query.lower()))
    matches = []

    for fac in FACULTY_LIST:
        name = fac.get("name", "").strip()
        dept = fac.get("department", "").strip()
        desig = fac.get("designation", "").strip()
        email = fac.get("email", "").strip()

        raw_tokens = [w for w in re.findall(r"[a-zA-Z]+", name.lower()) if w not in FACULTY_TITLES]
        if not raw_tokens:
            continue

        distinctive = [w for w in raw_tokens if w not in COMMON_NAME_TOKENS]
        matched_tokens = [w for w in raw_tokens if w in q_tokens]

        is_match = False
        if distinctive and all(w in q_tokens for w in distinctive):
            is_match = True
        elif len(raw_tokens) >= 2 and len(matched_tokens) >= 2 and len(matched_tokens) == len(raw_tokens):
            is_match = True

        if is_match:
            details = [f"{name} is a {desig} in the {dept} department at GNDEC (Guru Nanak Dev Engineering College)."]
            if email:
                details.append(f"- **Email:** {email}")
            if fac.get("qualification"):
                details.append(f"- **Qualification:** {fac['qualification']}")
            if fac.get("experience"):
                details.append(f"- **Experience:** {fac['experience']}")
            if fac.get("research_interest"):
                details.append(f"- **Research Interests:** {fac['research_interest']}")
            if fac.get("publications_journal"):
                details.append(f"- **Journal Publications:** {fac['publications_journal']}")
            if fac.get("publications_conference"):
                details.append(f"- **Conference Publications:** {fac['publications_conference']}")
            if fac.get("memberships"):
                details.append(f"- **Professional Memberships:** {fac['memberships']}")
            if fac.get("profile_url"):
                details.append(f"- **Official Profile:** {fac['profile_url']}")

            doc_data = {
                "question": f"Who is {name}? What is the contact email, designation, qualification, and research interest of {name} in {dept}?",
                "answer": "\n".join(details),
                "section": f"Faculty Directory - {dept}",
                "source_file": "faculty.json",
                "is_aggregate": False
            }
            if fac.get("profile_url"):
                doc_data["doc_url"] = fac["profile_url"]
            matches.append((len(matched_tokens), metadata_to_doc(doc_data)))

    matches.sort(key=lambda x: x[0], reverse=True)
    return [m[1] for m in matches[:3]]


# ----------------------------------------------------
# Structured Fee Matcher (100% Precision Fee Table Lookup)
# ----------------------------------------------------
PROG_PATTERNS = {
    "b.tech": re.compile(r"\b(b\.?tech|btech|b\s+tech|bachelor of technology)\b", re.IGNORECASE),
    "lateral": re.compile(r"\b(lateral|leet|diploma to degree|lateral entry)\b", re.IGNORECASE),
    "m.tech": re.compile(r"\b(m\.?tech|mtech|m\s+tech|master of technology)\b", re.IGNORECASE),
    "mba": re.compile(r"\b(mba|master of business administration)\b", re.IGNORECASE),
    "mca": re.compile(r"\b(mca|master of computer applications)\b", re.IGNORECASE),
    "bba": re.compile(r"\b(bba|bachelor of business administration)\b", re.IGNORECASE),
    "bca": re.compile(r"\b(bca|bachelor of computer applications)\b", re.IGNORECASE),
    "b.voc": re.compile(r"\b(b\.?voc|bvoc|interior design)\b", re.IGNORECASE),
    "b.arch": re.compile(r"\b(b\.?arch|barch|architecture)\b", re.IGNORECASE),
    "b.com": re.compile(r"\b(b\.?com|bcom|entrepreneurship)\b", re.IGNORECASE)
}

def find_fee_structure_matches(query: str) -> List[Document]:
    """Finds exact or high-confidence fee structure tables when fees are requested."""
    if not FEE_LIST:
        return []

    q_lower = query.lower()
    # If the user is asking about fees of another college/institution, do not route to GNDEC fee tables
    ext_matches = [
        r"\b(iit|iits|nit|nits|iiit|bits|thapar|lpu|cu|chitkara|amity|cgc|sliet|mrsptu|panjab university|pu chd|delhi university|du|harvard|mit|stanford)\b"
    ]
    if any(re.search(pat, q_lower) for pat in ext_matches) and not re.search(r"\b(gndec|gne|here|our)\b", q_lower):
        return []

    # Procedural / conceptual fee or scholarship queries should NOT return raw fee tables
    procedural_keywords = [
        "how to pay", "how can students pay", "how can i pay", "mode of payment",
        "payment mode", "payment method", "online payment", "fee payment", "pay fee", "pay fees", "pay college",
        "who is eligible", "eligibility", "criteria for tfw", "scholarship scheme",
        "scholarships available", "financial aid", "needy students", "pms scheme",
        "post matric scholarship scheme", "tfw scheme", "tuition fee waiver scheme"
    ]
    if any(pk in q_lower for pk in procedural_keywords):
        return []

    fee_keywords = {"fee", "fees", "cost", "kharcha", "paisa", "fee structure", "hostel fee", "tuition", "tution"}
    if not any(k in q_lower for k in fee_keywords):
        return []

    # If asking specifically for fee amount under TFW/PMS, return fee tables
    if re.search(r"\b(tfw fee|pms fee|fee under tfw|fee under pms|fee.*tfw|fee.*pms)\b", q_lower):
        return [metadata_to_doc(item) for item in FEE_LIST]

    matched = []
    found_specific = False

    # Match specific program patterns
    for fee_item in FEE_LIST:
        q_item = fee_item.get("question", "").lower()
        for prog_key, pattern in PROG_PATTERNS.items():
            if pattern.search(query):
                if prog_key in q_item:
                    matched.append(metadata_to_doc(fee_item))
                    found_specific = True

    # If general fee question without specific course or only 'college fee'
    if not found_specific and any(w in q_lower for w in ["fee", "fees", "fee structure", "hostel"]):
        matched = [metadata_to_doc(item) for item in FEE_LIST]

    return matched


# ----------------------------------------------------
# Structured Courses Matcher (verified B.Tech/PG branches)
# ----------------------------------------------------
COURSE_EXPLICIT_PATTERNS = re.compile(
    r"\b("
    r"(what|which|list|tell me about|how many)\s+(are\s+the\s+|the\s+)?(all\s+)?(b\.?tech\s+|m\.?tech\s+|pg\s+|ug\s+|undergraduate\s+|postgraduate\s+|engineering\s+)?(branches|courses|programs|programmes|degrees|streams|disciplines)|"
    r"(branches|courses|programs|programmes|degrees|streams|disciplines)\s+(offered|available|taught|running|present)\s+(in|at|by)\s+(gndec|gne|the college|college)|"
    r"what\s+(b\.?tech|m\.?tech|pg|ug)\s+(branches|courses|programs|specializations)|"
    r"(b\.?tech|m\.?tech|pg|ug)\s+(branches|courses|specializations)|"
    r"(undergraduate|postgraduate|pg|ug)\s+(courses|programs|degrees)\s+(available|offered)"
    r")\b",
    re.IGNORECASE,
)

def find_courses_matches(query: str) -> List[Document]:
    """Returns verified course/program data when the query specifically asks about branches, courses, or degree programs."""
    if not COURSES_LIST:
        return []

    q_lower = query.lower()

    # Exclude facility/sports/library/hostel/fee/placement queries from course routing
    facility_keywords = {"facility", "facilities", "library", "sports", "gym", "gymnasium", "hostel", "mess", "canteen", "medical", "hospital", "dispensary", "fee", "fees", "placement", "faculty", "hod"}
    if any(k in q_lower for k in facility_keywords) and not re.search(r"\b(course|courses|program|programs|branch|branches|degree|degrees)\b", q_lower):
        return []

    if not COURSE_EXPLICIT_PATTERNS.search(query):
        return []

    # Check for specific subset (e.g. B.Tech branches specifically vs PG courses)
    if re.search(r"\b(b\.?tech|engineering|ug|undergraduate)\s+(branches|courses|programs|streams)\b", q_lower) or re.search(r"\bwhat\s+b\.?tech\s+branches\b", q_lower):
        btech_doc = [item for item in COURSES_LIST if "B.Tech branches" in item.get("question", "")]
        if btech_doc:
            return [metadata_to_doc(btech_doc[0])]

    if re.search(r"\b(pg|postgraduate|m\.?tech|mba|mca|master)\s+(courses|programs|degrees)\b", q_lower):
        pg_doc = [item for item in COURSES_LIST if "postgraduate" in item.get("question", "").lower()]
        if pg_doc:
            return [metadata_to_doc(pg_doc[0])]

    return [metadata_to_doc(item) for item in COURSES_LIST]


# ----------------------------------------------------
# Structured Admission Process Matcher
# ----------------------------------------------------
ADMISSION_KEYWORDS = re.compile(
    r"\b(how (to|do i|can i) (apply|register|get admission)|admission (process|procedure|steps)|"
    r"entrance (exam|test)|need (any )?(exam|jee|gate)|gate (score|exam|required)|"
    r"jee main (required|needed)|apply for admission|spot admission|seat allotment process|"
    r"admission.*counseling process|counseling process)\b",
    re.IGNORECASE,
)

def find_admission_matches(query: str) -> List[Document]:
    """Returns verified admission-process data when the query asks about application/entrance exam procedures."""
    if not ADMISSION_LIST:
        return []
    if not ADMISSION_KEYWORDS.search(query):
        return []
    return [metadata_to_doc(item) for item in ADMISSION_LIST]


# ----------------------------------------------------
# Hybrid Retrieval with Cross-Encoder Re-ranking
# ----------------------------------------------------
def retrieve(query: str, k: int = 6, min_score: float = -11.0) -> List[Document]:
    """
    Hybrid Retriever:
    1. Structured Entity Lookup (Faculty & Fee Structures)
    2. Dense FAISS Search (Top 10)
    3. Sparse BM25 Search (Top 10)
    4. Cross-Encoder Re-Ranking & Top-k Selection
    """
    logger.info(f"[RAG] Retrieving for query: {query!r}")

    # 1. Structured matches
    faculty_docs = find_faculty_matches(query)
    fee_docs = find_fee_structure_matches(query)
    course_docs = find_courses_matches(query)
    if fee_docs:
        # Structured fee docs have 100% official tables. Return ALL matched fee docs directly.
        logger.info(f"[RAG] Returning {len(fee_docs)} structured fee documents.")
        return fee_docs

    if faculty_docs and any(getattr(d, "metadata", {}).get("is_aggregate") for d in faculty_docs):
        # Aggregate faculty queries (PhD lists, HOD lists, Department rosters) have 100% precision tables.
        logger.info(f"[RAG] Returning {len(faculty_docs)} structured aggregate faculty documents.")
        return faculty_docs

    if course_docs:
        # Course/program queries return verified branches from courses_offered.json
        # — this prevents the LLM from hallucinating fake branches (Chemical, Biotech, etc.)
        logger.info(f"[RAG] Returning {len(course_docs)} verified structured course documents.")
        return course_docs

    admission_docs = find_admission_matches(query)
    if admission_docs:
        # Admission-process queries return verified procedures, plus top FAISS/BM25 context below.
        logger.info(f"[RAG] Returning {len(admission_docs)} verified admission-process documents.")
        return admission_docs

    structured_docs = faculty_docs

    # 2. Dense FAISS
    query_vec = embed_model.encode([query], convert_to_numpy=True, show_progress_bar=False).astype("float32")
    faiss.normalize_L2(query_vec)
    faiss_scores, faiss_ids = faiss_index.search(query_vec, 10)

    # 3. Sparse BM25
    q_tokens = _tokenize(query)
    bm25_ids = bm25_index.get_top_n(q_tokens, range(len(META)), n=10)

    # Union candidate indices
    candidate_indices = []
    seen = set()

    for idx in faiss_ids[0]:
        if idx >= 0 and idx not in seen:
            seen.add(int(idx))
            candidate_indices.append(int(idx))

    for idx in bm25_ids:
        if idx not in seen:
            seen.add(int(idx))
            candidate_indices.append(int(idx))

    if not candidate_indices and not structured_docs:
        return []

    # 4. Cross-Encoder Re-Ranking
    candidates = [META[i] for i in candidate_indices]
    pairs = [
        (query, f"Q: {c.get('question', '')}\nA: {c.get('answer', '')[:250]}\nSection: {c.get('section', '')}")
        for c in candidates
    ]

    scores = cross_encoder.predict(pairs, show_progress_bar=False)
    scored_candidates = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)

    # 5. Filter by confidence threshold
    top_docs: List[Document] = list(structured_docs)
    seen_contents = {d.page_content for d in top_docs}

    for score, item in scored_candidates:
        if len(top_docs) >= k:
            break
        # Skip outdated/corrupted legacy fee chunks if structured fee docs exist
        if fee_docs and ("Sr No. | Name of Program" in item.get("answer", "") or "Hostel Fee | Post Matric" in item.get("answer", "")):
            continue
        if float(score) >= min_score:
            doc = metadata_to_doc(item)
            if doc.page_content not in seen_contents:
                seen_contents.add(doc.page_content)
                top_docs.append(doc)

    logger.info(f"[RAG] Returning {len(top_docs)} top documents (Threshold: {min_score})")
    return top_docs


def get_retriever(k: int = 6):
    """Retriever factory compatible with LangChain agent callers."""
    def _retriever_fn(query: str) -> List[Document]:
        return retrieve(query, k=k)
    return _retriever_fn


retriever = get_retriever(k=6)
