# backend/vectorstore.py
import os
import re
import json
import faiss
import logging
import torch
import threading
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

# Paths for curated and dynamically learned datasets
EXTERNAL_PATH = os.path.join(DATA_DIR, "external_facts.json")
COURSES_PATH = os.path.join(DATA_DIR, "courses_offered.json")
ADMISSION_PATH = os.path.join(DATA_DIR, "admission_process.json")
LEARNED_PATH = os.path.join(DATA_DIR, "learned_facts.json")

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
MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "intfloat/multilingual-e5-small")
IS_E5_MODEL = "e5" in MODEL_NAME.lower()
logger.info(f"Loading embedding model: {MODEL_NAME} on CPU")
embed_model = SentenceTransformer(MODEL_NAME, device="cpu")

# Cross-Encoder Re-ranker (CPU)
RERANKER_MODEL_NAME = os.getenv("RERANKER_MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2")
logger.info(f"Loading Cross-Encoder reranker: {RERANKER_MODEL_NAME} on CPU")
cross_encoder = CrossEncoder(RERANKER_MODEL_NAME, device="cpu")

# Retrieval tuning (env-tunable for production / calibration sweeps)
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "6"))                 # docs passed to the LLM
RERANK_MIN_SCORE = float(os.getenv("RERANK_MIN_SCORE", "-11.0")) # cross-encoder score floor


def format_query_embedding_input(query: str) -> str:
    """Format query based on model requirements (e.g., e5 models require 'query: ' prefix)."""
    q_str = query.strip()
    if IS_E5_MODEL:
        return f"query: {q_str}"
    return q_str


def encode_query(query: str):
    """Encodes query into L2-normalized dense vector for semantic search and caching."""
    q_formatted = format_query_embedding_input(query)
    vec = embed_model.encode([q_formatted], convert_to_numpy=True, show_progress_bar=False).astype("float32")
    faiss.normalize_L2(vec)
    return vec[0]


def metadata_to_doc(item: Dict[str, Any]) -> Document:
    """Convert metadata record into LangChain Document"""
    text = f"Q: {item['question']}\nA: {item['answer']}\nSection: {item.get('section', 'General')}"
    return Document(page_content=text, metadata=item)


# Lightweight tokenization for BM25 (Unicode-aware to support Punjabi/Hindi/English)
def _tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())


# ----------------------------------------------------
# Thread-safe Dynamic Index Synchronization & Ingestion
# ----------------------------------------------------
_vector_store_lock = threading.Lock()
seen_qs = {m.get("question", "").strip().lower() for m in META}
seen_answers = {m.get("answer", "")[:120].strip().lower() for m in META if m.get("answer")}

# 1. Synchronize any unindexed facts from curated/learned files on startup
curated_files = [EXTERNAL_PATH, COURSES_PATH, FEE_PATH, ADMISSION_PATH, LEARNED_PATH]
pending_items: List[Dict[str, Any]] = []
for file_path in curated_files:
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                records = json.load(f)
                for item in records:
                    q = item.get("question", "").strip()
                    ans = item.get("answer", "").strip()
                    if q and q.lower() not in seen_qs and ans[:120].lower() not in seen_answers:
                        pending_items.append(item)
                        seen_qs.add(q.lower())
                        if ans:
                            seen_answers.add(ans[:120].lower())
        except Exception as e:
            logger.warning(f"Could not load curated facts from {file_path}: {e}")

if pending_items:
    logger.info(f"⚡ Indexing {len(pending_items)} curated/learned facts into FAISS vector database...")
    passages = [
        f"passage: Q: {it.get('question', '')}\nA: {it.get('answer', '')}\nSection: {it.get('section', 'General')}"
        if IS_E5_MODEL
        else f"Q: {it.get('question', '')}\nA: {it.get('answer', '')}\nSection: {it.get('section', 'General')}"
        for it in pending_items
    ]
    vecs = embed_model.encode(passages, convert_to_numpy=True, show_progress_bar=False).astype("float32")
    faiss.normalize_L2(vecs)
    faiss_index.add(vecs)
    META.extend(pending_items)
    try:
        faiss.write_index(faiss_index, INDEX_PATH)
        with open(META_PATH, "w", encoding="utf-8") as f:
            json.dump(META, f)
        logger.info(f"✅ FAISS synchronized on startup: {faiss_index.ntotal} vectors matches {len(META)} metadata entries.")
    except Exception as e:
        logger.warning(f"Could not persist synchronized FAISS index: {e}")

# Recover if FAISS vectors and META ever fell out of sync
if faiss_index.ntotal < len(META):
    missing_items = META[faiss_index.ntotal:]
    logger.info(f"⚡ Recovering {len(missing_items)} unindexed items into FAISS vector store...")
    passages = [
        f"passage: Q: {it.get('question', '')}\nA: {it.get('answer', '')}\nSection: {it.get('section', 'General')}"
        if IS_E5_MODEL
        else f"Q: {it.get('question', '')}\nA: {it.get('answer', '')}\nSection: {it.get('section', 'General')}"
        for it in missing_items
    ]
    vecs = embed_model.encode(passages, convert_to_numpy=True, show_progress_bar=False).astype("float32")
    faiss.normalize_L2(vecs)
    faiss_index.add(vecs)
    try:
        faiss.write_index(faiss_index, INDEX_PATH)
    except Exception as e:
        logger.warning(f"Could not write recovered index: {e}")

logger.info("🔄 Building lightweight BM25 keyword index...")
# Index all documents including fee structures, syllabi, and newly indexed facts
bm25_corpus = [_tokenize(f"{m.get('question', '')} {m.get('section', '')}") for m in META]
bm25_index = BM25Okapi(bm25_corpus)
logger.info(f"✅ BM25 index built successfully with {len(bm25_corpus)} documents.")


def add_to_vector_db(items: List[Dict[str, Any]], persist: bool = True) -> int:
    """
    Dynamically embed and add new facts/web search results into the runtime FAISS vector index,
    metadata store, and BM25 index. Automatically persists to disk so subsequent queries
    find them locally without re-hitting external services.

    Deduplication rules:
      - Ignores items with existing question or near-identical answer snippet.
      - Enforces strict GNDEC domain check on URLs.
    Returns the count of newly indexed documents.
    """
    if not items:
        return 0

    to_add: List[Dict[str, Any]] = []
    with _vector_store_lock:
        for it in items:
            if not isinstance(it, dict):
                continue
            q = (it.get("question") or it.get("title") or "").strip()
            a = (it.get("answer") or it.get("content") or "").strip()
            # Clean snippet headers like [WEB], [WEB-ANSWER], [WEB-KNOWLEDGE]
            a = re.sub(r"^\[WEB(?:-[A-Z]+)?\]\s*", "", a).strip()
            if not q or not a or len(a) < 10:
                continue

            q_key = q.lower()
            a_key = a[:120].lower()
            if q_key in seen_qs or a_key in seen_answers:
                continue

            url = it.get("url") or it.get("metadata", {}).get("url") or ""
            # Guardrail: if a URL is provided, ensure it belongs strictly to gndec.ac.in
            if url:
                try:
                    from .web_search import is_gndec_domain
                    if not is_gndec_domain(url):
                        continue
                except Exception:
                    pass

            sec = it.get("section") or it.get("metadata", {}).get("section") or "Web Search Knowledge"
            src = (
                it.get("source_file")
                or it.get("url")
                or it.get("metadata", {}).get("url")
                or it.get("metadata", {}).get("source_file")
                or "gndec.ac.in"
            )

            entry = {
                "question": q,
                "answer": a,
                "section": sec,
                "source_file": src,
                "url": url,
                "metadata": it.get("metadata", {}),
            }
            to_add.append(entry)
            seen_qs.add(q_key)
            seen_answers.add(a_key)

        if not to_add:
            return 0

        try:
            passages = [
                f"passage: Q: {entry['question']}\nA: {entry['answer']}\nSection: {entry['section']}"
                if IS_E5_MODEL
                else f"Q: {entry['question']}\nA: {entry['answer']}\nSection: {entry['section']}"
                for entry in to_add
            ]
            vecs = embed_model.encode(passages, convert_to_numpy=True, show_progress_bar=False).astype("float32")
            faiss.normalize_L2(vecs)
            faiss_index.add(vecs)
            META.extend(to_add)

            # Update BM25
            global bm25_corpus, bm25_index
            new_tokens = [_tokenize(f"{entry['question']} {entry['section']}") for entry in to_add]
            bm25_corpus.extend(new_tokens)
            bm25_index = BM25Okapi(bm25_corpus)

            logger.info(f"✅ Dynamic Indexing: Added {len(to_add)} documents to FAISS & BM25 (total {faiss_index.ntotal} docs).")

            if persist:
                try:
                    faiss.write_index(faiss_index, INDEX_PATH)
                    with open(META_PATH, "w", encoding="utf-8") as f:
                        json.dump(META, f)

                    # Persist to learned_facts.json without duplicates
                    learned_items: List[Dict[str, Any]] = []
                    if os.path.exists(LEARNED_PATH):
                        try:
                            with open(LEARNED_PATH, "r", encoding="utf-8") as f:
                                learned_items = json.load(f)
                        except Exception:
                            learned_items = []
                    existing_learned_ans = {it.get("answer", "")[:120].strip().lower() for it in learned_items if it.get("answer")}
                    for entry in to_add:
                        if entry.get("answer", "")[:120].strip().lower() not in existing_learned_ans:
                            learned_items.append(entry)
                            existing_learned_ans.add(entry.get("answer", "")[:120].strip().lower())

                    with open(LEARNED_PATH, "w", encoding="utf-8") as f:
                        json.dump(learned_items, f, indent=2)
                    logger.info(f"💾 Successfully persisted {len(to_add)} learned facts to disk.")
                except Exception as e:
                    logger.warning(f"Could not persist newly indexed items: {e}")

            return len(to_add)
        except Exception as e:
            logger.error(f"Failed to dynamically add items to vector DB: {e}")
            return 0


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


def _format_faculty_subject_table(members: List[Dict[str, Any]], title: str, include_dept: bool = False) -> str:
    lines = [f"### {title}\n"]
    if include_dept:
        lines.append("| Sr No. | Name | Designation | Department | Subjects Taught / Areas of Specialization | Email |")
        lines.append("| :---: | :--- | :--- | :--- | :--- | :--- |")
        for i, m in enumerate(members, 1):
            ri = m.get("research_interest", "").strip()
            if not ri or ri in ["-", "N.A.", "Nil"]:
                ri = m.get("qualification", "").strip() or m.get("department", "")
            ri = ri.replace("\n", " ").replace("|", "/")
            if len(ri) > 95:
                ri = ri[:92] + "..."
            lines.append(f"| {i} | {m['name']} | {m['designation']} | {m['department']} | {ri} | {m['email']} |")
    else:
        lines.append("| Sr No. | Name | Designation | Subjects Taught / Areas of Specialization | Email |")
        lines.append("| :---: | :--- | :--- | :--- | :--- |")
        for i, m in enumerate(members, 1):
            ri = m.get("research_interest", "").strip()
            if not ri or ri in ["-", "N.A.", "Nil"]:
                ri = m.get("qualification", "").strip() or m.get("department", "")
            ri = ri.replace("\n", " ").replace("|", "/")
            if len(ri) > 95:
                ri = ri[:92] + "..."
            lines.append(f"| {i} | {m['name']} | {m['designation']} | {ri} | {m['email']} |")
    return "\n".join(lines)


SUBJECT_FACULTY_PATTERNS = re.compile(
    r"\b("
    r"(?:list|tell me|who are|names? of)\s+(?:the\s+)?(?:all\s+)?facult(?:y|ies| members?)\s+(?:according to|by|based on|with)\s+(?:the\s+)?(?:subjects?|topics?|courses?|specializations?|areas?)(?:\s+(?:they\s+)?teach|\s+taught|\s+specialization)?|"
    r"facult(?:y|ies| members?)\s+(?:according to|by|based on|with)\s+(?:the\s+)?(?:subjects?|topics?|courses?|specializations?|areas?)|"
    r"(?:subjects?|courses?)\s+(?:taught by|handled by|allotted to)\s+(?:the\s+)?facult(?:y|ies| members?)|"
    r"who teaches (?:what|which subject|which course)|"
    r"(?:which|what) facult(?:y|ies| professor| teacher)\s+teaches?\b|"
    r"facult(?:y|ies)\s+(?:teaching\s+subjects?|specializations?|research interests?)|"
    r"who teaches\s+[a-zA-Z\s]+"
    r")\b",
    re.IGNORECASE,
)


def find_faculty_matches(query: str) -> List[Document]:
    """Finds exact or aggregate faculty matches from structured records."""
    if not FACULTY_LIST:
        return []

    q_lower = query.lower()
    ext_matches = [
        r"\b(iit|iits|nit|nits|iiit|bits|thapar|lpu|cu|chitkara|amity|cgc|sliet|mrsptu|panjab university|pu chd|delhi university|du|harvard|mit|stanford|gndu|guru nanak dev university|gndpc|guru nanak dev polytechnic|gndit|gniet|gnit|sgnd khalsa|guru nanak khalsa|gnkc|ggn khalsa|guru nanak college of education|guru nanak institute of management|gnim)\b"
    ]
    if any(re.search(pat, q_lower) for pat in ext_matches) and not re.search(r"\b(gndec|gne|here|our)\b", q_lower):
        return []

    matched_dept = None
    for dept, pat in DEPT_PATTERNS.items():
        if pat.search(query):
            matched_dept = dept
            break

    # 1. Faculty by Subjects Taught & Specialization Query
    if SUBJECT_FACULTY_PATTERNS.search(query):
        if matched_dept:
            dept_fac = [m for m in FACULTY_LIST if m.get("department") == matched_dept]
            table_md = _format_faculty_subject_table(dept_fac, f"Faculty Directory by Subjects Taught & Specialization - {matched_dept}")
            doc_data = {
                "question": f"What is the list of faculty members in {matched_dept} according to the subjects they teach at GNDEC?",
                "answer": table_md,
                "section": f"Faculty Directory - Subjects in {matched_dept}",
                "source_file": "faculty.json",
                "is_aggregate": True
            }
            return [metadata_to_doc(doc_data)]
        else:
            # Check if asking about a specific subject/area (e.g. "who teaches machine learning" or "who teaches surveying")
            q_clean = re.sub(
                r"\b(who|which|what|tell|me|list|all|faculty|faculties|members?|professors?|teachers?|according|to|based|on|the|subjects?|courses?|topics?|teach|teaches|taught|at|in|of|gndec|gne|college)\b",
                "",
                q_lower,
            )
            candidate_tokens = [w for w in re.findall(r"[a-zA-Z]+", q_clean) if len(w) >= 3]
            specific_matches = []
            if candidate_tokens and len(candidate_tokens) <= 4:
                phrase = " ".join(candidate_tokens)
                for m in FACULTY_LIST:
                    ri = (m.get("research_interest", "") + " " + m.get("qualification", "")).lower()
                    if phrase in ri or (len(candidate_tokens) == 1 and candidate_tokens[0] in ri):
                        specific_matches.append(m)

            if specific_matches:
                subj_title = " ".join(candidate_tokens).title()
                table_md = _format_faculty_subject_table(
                    specific_matches,
                    f"Faculty Members Specializing in / Teaching {subj_title} at GNDEC",
                    include_dept=True,
                )
                doc_data = {
                    "question": f"Which faculty members teach or specialize in {subj_title} at Guru Nanak Dev Engineering College (GNDEC)?",
                    "answer": table_md,
                    "section": f"Faculty Directory - {subj_title}",
                    "source_file": "faculty.json",
                    "is_aggregate": True,
                }
                return [metadata_to_doc(doc_data)]
            else:
                # General query across all departments: build comprehensive departmental directory
                by_dept = {}
                for m in FACULTY_LIST:
                    d = m.get("department", "Other")
                    by_dept.setdefault(d, []).append(m)

                lines = [
                    "Guru Nanak Dev Engineering College (GNDEC), Ludhiana has over 270 distinguished faculty members across its academic departments.\n",
                    "Here is the directory of faculty members according to the subjects and academic specializations they teach across the departments:\n"
                ]
                academic_depts = [
                    "Computer Science & Engg.", "Information Technology", "Mechanical Engineering",
                    "Civil Engineering", "Electrical Engineering", "Electronics & Communication Engineering",
                    "Business Administration", "Computer Applications", "Applied Science",
                    "Production Engineering", "School of Architecture"
                ]
                for d in academic_depts:
                    members = by_dept.get(d, [])
                    if members:
                        lines.append(_format_faculty_subject_table(members, d, include_dept=False))
                        lines.append("")

                full_md = "\n".join(lines)
                doc_data = {
                    "question": "What is the list of faculty members at Guru Nanak Dev Engineering College (GNDEC) according to the subjects they teach and their areas of specialization?",
                    "answer": full_md,
                    "section": "Faculty Directory - Subjects Taught",
                    "source_file": "faculty.json",
                    "is_aggregate": True,
                }
                return [metadata_to_doc(doc_data)]

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
        r"\b(iit|iits|nit|nits|iiit|bits|thapar|lpu|cu|chitkara|amity|cgc|sliet|mrsptu|panjab university|pu chd|delhi university|du|harvard|mit|stanford|gndu|guru nanak dev university|gndpc|guru nanak dev polytechnic|gndit|gniet|gnit|sgnd khalsa|guru nanak khalsa|gnkc|ggn khalsa|guru nanak college of education|guru nanak institute of management|gnim)\b"
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
    ext_matches = [
        r"\b(iit|iits|nit|nits|iiit|bits|thapar|lpu|cu|chitkara|amity|cgc|sliet|mrsptu|panjab university|pu chd|delhi university|du|harvard|mit|stanford|gndu|guru nanak dev university|gndpc|guru nanak dev polytechnic|gndit|gniet|gnit|sgnd khalsa|guru nanak khalsa|gnkc|ggn khalsa|guru nanak college of education|guru nanak institute of management|gnim)\b"
    ]
    if any(re.search(pat, q_lower) for pat in ext_matches) and not re.search(r"\b(gndec|gne|here|our)\b", q_lower):
        return []

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
    r"\b("
    r"how (to|do i|can i) (get admission|take admission|enroll|join)|"
    r"how (to|do i|can i) apply for (admission|b\.?tech|m\.?tech|mba|mca|bca|bba|leet|lateral|phd|course|college)|"
    r"admission (process|procedure|steps|criteria|rules|guidelines|schedule|notice)|"
    r"entrance (exam|exams|test|tests)|need (any )?(exam|jee|gate|cmat|nata)|"
    r"gate (score|exam|required)|jee main (required|needed)|"
    r"apply for admission|spot admission|spot counselling|seat allotment|"
    r"admission.*counseling|counseling process|"
    r"rural quota|rural reservation|rural category|rural area quota|rural students|"
    r"sikh minority quota|eligibility for admission"
    r")\b",
    re.IGNORECASE,
)

def find_admission_matches(query: str) -> List[Document]:
    """Returns verified admission-process data when the query asks about application, quotas, or entrance exam procedures."""
    if not ADMISSION_LIST:
        return []

    q_lower = query.lower()

    # If the user is asking about admissions of another college/institution, do not route to GNDEC admission data
    ext_matches = [
        r"\b(iit|iits|nit|nits|iiit|bits|thapar|lpu|cu|chitkara|amity|cgc|sliet|mrsptu|panjab university|pu chd|delhi university|du|harvard|mit|stanford|gndu|guru nanak dev university|gndpc|guru nanak dev polytechnic|gndit|gniet|gnit|sgnd khalsa|guru nanak khalsa|gnkc|ggn khalsa|guru nanak college of education|guru nanak institute of management|gnim)\b"
    ]
    if any(re.search(pat, q_lower) for pat in ext_matches) and not re.search(r"\b(gndec|gne|here|our)\b", q_lower):
        return []

    if not ADMISSION_KEYWORDS.search(query):
        return []

    # If the user is asking about admission to another college/institution, do not route to GNDEC admission records
    ext_matches = [
        r"\b(iit|iits|nit|nits|iiit|bits|thapar|lpu|cu|chitkara|amity|cgc|sliet|mrsptu|panjab university|pu chd|delhi university|du|harvard|mit|stanford|gndu|guru nanak dev university|gndpc|guru nanak dev polytechnic|gndit|gniet|gnit|sgnd khalsa|guru nanak khalsa|gnkc|ggn khalsa|guru nanak college of education|guru nanak institute of management|gnim)\b"
    ]
    if any(re.search(pat, q_lower) for pat in ext_matches) and not re.search(r"\b(gndec|gne|here|our)\b", q_lower):
        return []

    # Guard against non-admission queries (bus pass, railway concession, hostel, certificates)
    if re.search(r"\b(bus pass|buss pass|railway|concession|hostel|transport|no[- ]dues)\b", q_lower):
        return []

    # If specifically asking about rural quota / reservation
    if re.search(r"\b(rural|rural quota|rural reservation|rural category|rural area)\b", q_lower):
        rural_docs = [item for item in ADMISSION_LIST if "rural" in item.get("question", "").lower() or "rural quota" in item.get("answer", "").lower()]
        if rural_docs:
            return [metadata_to_doc(item) for item in rural_docs]

    # If specifically asking about BCA admission
    if re.search(r"\b(bca|bca admission|bca here)\b", q_lower):
        bca_docs = [item for item in ADMISSION_LIST if "bca" in item.get("question", "").lower()]
        if bca_docs:
            return [metadata_to_doc(item) for item in bca_docs]

    # If specifically asking about BBA / B.Com
    if re.search(r"\b(bba|b\.?com)\b", q_lower):
        bba_docs = [item for item in ADMISSION_LIST if "bba" in item.get("question", "").lower() or "b.com" in item.get("question", "").lower()]
        if bba_docs:
            return [metadata_to_doc(item) for item in bba_docs]

    # If specifically asking about B.Arch
    if re.search(r"\b(b\.?arch|architecture)\b", q_lower):
        arch_docs = [item for item in ADMISSION_LIST if "b.arch" in item.get("question", "").lower()]
        if arch_docs:
            return [metadata_to_doc(item) for item in arch_docs]

    # If specifically asking about Lateral Entry (LEET)
    if re.search(r"\b(leet|lateral entry|lateral)\b", q_lower):
        leet_docs = [item for item in ADMISSION_LIST if "lateral" in item.get("question", "").lower()]
        if leet_docs:
            return [metadata_to_doc(item) for item in leet_docs]

    # If specifically asking about Entrance Exams
    if re.search(r"\b(entrance exam|entrance test|jee main required|gate required|cmat required)\b", q_lower):
        exam_docs = [item for item in ADMISSION_LIST if "entrance exam" in item.get("question", "").lower()]
        if exam_docs:
            return [metadata_to_doc(item) for item in exam_docs]

    # If specifically asking about Quotas / Reservations
    if re.search(r"\b(quota|quotas|reservation|sikh minority|tfw|pms)\b", q_lower):
        quota_docs = [item for item in ADMISSION_LIST if "quota" in item.get("question", "").lower() or "reservation" in item.get("question", "").lower()]
        if quota_docs:
            return [metadata_to_doc(item) for item in quota_docs]

    # Default general admission query: return all verified admission docs
    return [metadata_to_doc(item) for item in ADMISSION_LIST]


# ----------------------------------------------------
# Structured Principal & Leadership Matcher
# ----------------------------------------------------
PRINCIPAL_PATTERNS = re.compile(
    r"\b("
    r"(list|names?|all|former|past|previous|succession|history)\s+(of\s+)?(all\s+)?(the\s+)?principals|"
    r"principals?\s+(till now|from college founded|from beginning|from founding|since inception|history|list|names?)|"
    r"(who (is|was|are)|tell me( about)?)\s+(the\s+)?(all\s+)?(first|current|past|former|previous)?\s*principals?|"
    r"principal(s)?\s+(list|name|names|desk)|"
    r"sehijpal singh|tara singh"
    r")\b",
    re.IGNORECASE,
)

def find_principal_matches(query: str) -> List[Document]:
    """Returns verified succession of principals from 1956 to present."""
    q_lower = query.lower()
    ext_matches = [
        r"\b(iit|iits|nit|nits|iiit|bits|thapar|lpu|cu|chitkara|amity|cgc|sliet|mrsptu|panjab university|pu chd|delhi university|du|harvard|mit|stanford|gndu|guru nanak dev university|gndpc|guru nanak dev polytechnic|gndit|gniet|gnit|sgnd khalsa|guru nanak khalsa|gnkc|ggn khalsa|guru nanak college of education|guru nanak institute of management|gnim)\b"
    ]
    if any(re.search(pat, q_lower) for pat in ext_matches) and not re.search(r"\b(gndec|gne|here|our)\b", q_lower):
        return []

    if not PRINCIPAL_PATTERNS.search(query):
        return []

    q_lower = query.lower()
    ext_matches = [
        r"\b(iit|iits|nit|nits|iiit|bits|thapar|lpu|cu|chitkara|amity|cgc|sliet|mrsptu|panjab university|pu chd|delhi university|du|harvard|mit|stanford|gndu|guru nanak dev university|gndpc|guru nanak dev polytechnic|gndit|gniet|gnit|sgnd khalsa|guru nanak khalsa|gnkc|ggn khalsa|guru nanak college of education|guru nanak institute of management|gnim)\b"
    ]
    if any(re.search(pat, q_lower) for pat in ext_matches) and not re.search(r"\b(gndec|gne|here|our)\b", q_lower):
        return []

    doc_data = {
        "question": "Who are all the principals of GNDEC from founding to current? What is the succession list of principals?",
        "answer": (
            "Guru Nanak Dev Engineering College (GNDEC), Ludhiana was established in 1956 under the Nankana Sahib Education Trust (NSET).\n\n"
            "### Succession List of Principals (from College Foundation to Present):\n\n"
            "1. **Principal Tara Singh (S. Tara Singh Randhawa)** (1956 – 1970):\n"
            "   - Foundational and longest-serving Principal of GNDEC (served 14 years).\n"
            "   - Spearheaded the institution through its formative era following the foundation stone laying by President Dr. Rajendra Prasad on April 8, 1956.\n"
            "   - The prestigious annual *Principal S. Tara Singh Scholarship* for best athlete honors his enduring legacy.\n\n"
            "2. **S. Hari Singh**:\n"
            "   - Early Principal and senior Professor of Electrical Engineering who established core academic departments and laboratories.\n\n"
            "3. **Dr. Randhir Singh Seehra (Dr. R.S. Seehra)**:\n"
            "   - Distinguished GNDEC alumnus (Mechanical Engineering, Batch of 1961) who later served as Principal of GNDEC, Ludhiana and Director of I.E.T. Bhaddal.\n\n"
            "4. **Dr. H. K. Buttar (H. S. Buttar)**:\n"
            "   - Former Principal and senior administrative leader of GNDEC.\n\n"
            "5. **Dr. Rupinder Pal Singh (Dr. R.P. Singh)**:\n"
            "   - Former Principal who guided curriculum expansion and modernization.\n\n"
            "6. **Dr. Manohar Singh Saini (Dr. M.S. Saini)**:\n"
            "   - Former Principal and Director who led GNDEC to autonomous status under UGC (2012), NAAC 'A' grade accreditation, and TEQIP-II implementation.\n\n"
            "7. **Dr. Sehijpal Singh (Dr. Sehijpal Singh Khangura)** (Current Principal):\n"
            "   - Qualifications: Ph.D. (IIT Roorkee), M.E. (GNDEC), B.E. (Mechanical Engineering, GNDEC Batch of 1990).\n"
            "   - Phone: 0161-5064501 | Email: principal@gndec.ac.in | Office: Principal Desk, Administrative Block, GNDEC Ludhiana.\n\n"
            "All principals have guided GNDEC under the founding motto 'Removal of Economic Backwardness through Technology' of Nankana Sahib Education Trust."
        ),
        "section": "Administration & Leadership",
        "source_file": "gndec.ac.in/about-us/principal-desk",
        "doc_url": "https://gndec.ac.in/?q=node/5",
        "is_aggregate": True,
    }
    return [metadata_to_doc(doc_data)]


# ----------------------------------------------------
# Structured FDP (Faculty Development Programme) Matcher
# ----------------------------------------------------
FDP_PATTERNS = re.compile(
    r"\b("
    r"fdp|fdps|faculty development program|faculty development programme|"
    r"which fdp|live fdp|active fdp|upcoming fdp|recent fdp"
    r")\b",
    re.IGNORECASE,
)

def find_fdp_matches(query: str) -> List[Document]:
    """Returns verified active, recent, and ongoing Faculty Development Programmes at GNDEC."""
    if not FDP_PATTERNS.search(query):
        return []

    doc_data = {
        "question": "Which FDP is currently live or active at GNDEC? What Faculty Development Programs (FDP) are conducted at GNDEC?",
        "answer": (
            "Guru Nanak Dev Engineering College (GNDEC), Ludhiana regularly conducts National and International Faculty Development Programmes (FDPs) under AICTE, ATAL Academy, ISTE, TEQIP, and IKGPTU sponsorship:\n\n"
            "### Active & Recent Faculty Development Programmes (FDPs):\n\n"
            "1. **National Level One-Week FDP on 'Design Thinking' (Human-Centred Innovation for Engineering Educators)**:\n"
            "   - Mode: Hybrid (includes a One-Day Industrial Visit)\n"
            "   - Organized by: Department of Computer Science & Engineering in association with Institution’s Innovation Council (IIC - MoE Initiative) under the aegis of IQAC, GNDEC.\n"
            "   - Focus: NEP 2020 Design Thinking core competencies, pedagogical frameworks, and prototyping for engineering faculty.\n\n"
            "2. **AICTE Training and Learning (ATAL) Academy FDP on 'Generative AI Unveiled: Concepts, Models, and Real-world Applications'**:\n"
            "   - Venue: ANJUMAN Seminar Hall, Department of Information Technology, GNDEC.\n"
            "   - Focus: Large Language Models (LLMs), prompt engineering, Generative AI models, and real-world implementations.\n\n"
            "3. **International Online e-FDP on 'Smart Health Innovation: Integrating Imaging, Sensors & Biomaterials'**:\n"
            "   - Focus: Medical informatics, CBIR, wearable sensors, and healthcare engineering applications.\n\n"
            "4. **AICTE-ISTE Sponsored FDP on 'Recent Trends in Image Processing Techniques'**:\n"
            "   - Department of Information Technology (Coordinator: Dr. Amit Kamra, amit_kamra@gndec.ac.in, Phone: 98142-29753).\n\n"
            "### How to Check Live/Upcoming FDPs & Register:\n"
            "- Visit the official notices section at **https://gndec.ac.in** under 'Campus News' and 'Information Corner'.\n"
            "- For AICTE ATAL FDPs, search and register through the AICTE ATAL portal (**https://www.aicte-india.org/atal**).\n"
            "- Department portals (cse.gndec.ac.in, it.gndec.ac.in, ece.gndec.ac.in) release department-specific registration links and Google Forms for each session."
        ),
        "section": "Faculty Development Programs",
        "source_file": "gndec.ac.in/fdp",
        "doc_url": "https://gndec.ac.in",
        "is_aggregate": True,
    }
    return [metadata_to_doc(doc_data)]


# ----------------------------------------------------
# Structured Student Services & Amenities Matcher
# ----------------------------------------------------
STUDENT_SERVICES_PATTERNS = re.compile(
    r"\b("
    r"bus pass|buss pass|bus form|buss pass form|how to apply for bus pass|"
    r"railway concession|railway form|"
    r"hostel (facility|facilities|accommodation|room|admission|fee)|"
    r"bonafide certificate|character certificate|migration (form|application|certificate)|"
    r"duplicate id card|new identity card|id card form|college identity card|"
    r"no[- ]dues form|no dues certificate"
    r")\b",
    re.IGNORECASE,
)

def find_student_services_matches(query: str) -> List[Document]:
    """Returns verified student amenities and download proforma facts (bus pass, railway, hostels, certificates)."""
    if not STUDENT_SERVICES_PATTERNS.search(query):
        return []

    q_lower = query.lower()
    matched_facts = []

    if os.path.exists(EXTERNAL_PATH):
        try:
            with open(EXTERNAL_PATH, "r", encoding="utf-8") as f:
                facts = json.load(f)
                for it in facts:
                    it_q = it.get("question", "").lower()
                    if ("bus pass" in q_lower or "buss pass" in q_lower) and "bus pass" in it_q:
                        matched_facts.append(it)
                    elif "railway" in q_lower and "railway" in it_q:
                        matched_facts.append(it)
                    elif "hostel" in q_lower and "hostel" in it_q:
                        matched_facts.append(it)
                    elif ("certificate" in q_lower or "migration" in q_lower) and ("certificate" in it_q or "migration" in it_q):
                        matched_facts.append(it)
        except Exception as e:
            logger.warning(f"Could not load external facts for student services: {e}")

    return [metadata_to_doc(it) for it in matched_facts]


# ----------------------------------------------------
# Hybrid Retrieval with Cross-Encoder Re-ranking
# ----------------------------------------------------
def reciprocal_rank_fusion(dense_ids: List[int], sparse_ids: List[int], k: int = 60) -> List[int]:
    """Combines dense and sparse rankings using Reciprocal Rank Fusion."""
    rrf_scores = {}
    for rank, doc_id in enumerate(dense_ids):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank + 1))
    for rank, doc_id in enumerate(sparse_ids):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank + 1))

    # Sort by descending RRF score
    return sorted(rrf_scores.keys(), key=lambda doc_id: rrf_scores[doc_id], reverse=True)


def retrieve(query: str, k: int = RETRIEVAL_K, min_score: float = RERANK_MIN_SCORE) -> List[Document]:
    """
    Hybrid Retriever:
    1. Structured Entity Lookup (Faculty & Fee Structures)
    2. Dense FAISS Search (Top 30)
    3. Sparse BM25 Search (Top 30)
    4. Reciprocal Rank Fusion
    5. Cross-Encoder Re-Ranking & Top-k Selection
    """
    logger.info(f"[RAG] Retrieving for query: {query!r}")

    # 1. Structured matches
    principal_docs = find_principal_matches(query)
    if principal_docs:
        logger.info(f"[RAG] Returning {len(principal_docs)} structured principal documents.")
        return principal_docs

    fdp_docs = find_fdp_matches(query)
    if fdp_docs:
        logger.info(f"[RAG] Returning {len(fdp_docs)} structured FDP documents.")
        return fdp_docs

    student_services_docs = find_student_services_matches(query)
    if student_services_docs:
        logger.info(f"[RAG] Returning {len(student_services_docs)} structured student services documents.")
        return student_services_docs

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

    # 2. Dense FAISS (increase top-N for better recall before fusion)
    DENSE_TOP_N = int(os.getenv("DENSE_TOP_N", "30"))
    q_formatted = format_query_embedding_input(query)
    query_vec = embed_model.encode([q_formatted], convert_to_numpy=True, show_progress_bar=False).astype("float32")
    faiss.normalize_L2(query_vec)
    faiss_scores, faiss_ids = faiss_index.search(query_vec, DENSE_TOP_N)

    # 3. Sparse BM25 (increase top-N for better recall before fusion)
    SPARSE_TOP_N = int(os.getenv("SPARSE_TOP_N", "30"))
    q_tokens = _tokenize(query)
    bm25_ids = bm25_index.get_top_n(q_tokens, range(len(META)), n=SPARSE_TOP_N)

    # 4. Reciprocal Rank Fusion
    candidate_indices = reciprocal_rank_fusion(
        [int(i) for i in faiss_ids[0] if i >= 0],
        bm25_ids,
        k=60  # typical RRF constant
    )

    if not candidate_indices and not structured_docs:
        return []

    # 5. Cross-Encoder Re-Ranking (limit candidates to top-N for fast CPU inference)
    cross_encoder_top_n = int(os.getenv("CROSS_ENCODER_TOP_N", "12"))
    top_candidate_indices = candidate_indices[:cross_encoder_top_n]
    candidates = [META[i] for i in top_candidate_indices]
    pairs = [
        (query, f"Q: {c.get('question', '')}\nA: {c.get('answer', '')}\nSection: {c.get('section', '')}")
        for c in candidates
    ]

    scores = cross_encoder.predict(pairs, show_progress_bar=False)
    scored_candidates = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)

    # 6. Filter by confidence threshold
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


retriever = get_retriever(k=RETRIEVAL_K)
