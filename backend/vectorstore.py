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

if not os.path.exists(INDEX_PATH) or not os.path.exists(META_PATH):
    raise RuntimeError(
        f"FAISS index or meta.json missing!\nRun: python backend/build_vector_db.py"
    )

logger.info("🔄 Loading FAISS index & metadata...")
faiss_index = faiss.read_index(INDEX_PATH)

with open(META_PATH, "r", encoding="utf-8") as f:
    META: List[Dict[str, Any]] = json.load(f)

# Structured Faculty Data
FACULTY_LIST: List[Dict[str, Any]] = []
if os.path.exists(FACULTY_PATH):
    try:
        with open(FACULTY_PATH, "r", encoding="utf-8") as f:
            FACULTY_LIST = json.load(f)
        logger.info(f"Loaded {len(FACULTY_LIST)} faculty members for structured lookup.")
    except Exception as e:
        logger.warning(f"Could not load faculty.json: {e}")

# Embedding Model (CPU)
MODEL_NAME = "all-MiniLM-L6-v2"
logger.info(f"Loading embedding model: {MODEL_NAME} on CPU")
embed_model = SentenceTransformer(MODEL_NAME, device="cpu")

# Cross-Encoder Re-ranker (CPU)
RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
logger.info(f"Loading Cross-Encoder reranker: {RERANKER_MODEL_NAME} on CPU")
cross_encoder = CrossEncoder(RERANKER_MODEL_NAME, device="cpu")


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
FACULTY_TITLES = {"dr", "er", "prof", "mr", "ms", "mrs"}
COMMON_NAME_TOKENS = {
    "dr", "er", "prof", "mr", "ms", "mrs", "singh", "kaur", "kumar",
    "sharma", "gndec", "the", "is", "who", "what", "email", "contact",
    "of", "in", "department", "and", "faculty", "teacher", "hod", "head"
}

def find_faculty_matches(query: str) -> List[Document]:
    """Finds exact or high-confidence faculty matches from structured records."""
    if not FACULTY_LIST:
        return []

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
            doc_data = {
                "question": f"Who is {name}? What is the contact email and designation for {name} in {dept}?",
                "answer": f"{name} is a {desig} in the {dept} department at GNDEC. You can contact them via email at {email}.",
                "section": "Faculty Directory",
                "source_file": "faculty.json"
            }
            matches.append((len(matched_tokens), metadata_to_doc(doc_data)))

    matches.sort(key=lambda x: x[0], reverse=True)
    return [m[1] for m in matches[:3]]


# ----------------------------------------------------
# Hybrid Retrieval with Cross-Encoder Re-ranking
# ----------------------------------------------------
def retrieve(query: str, k: int = 6, min_score: float = -11.0) -> List[Document]:
    """
    Hybrid Retriever:
    1. Structured Entity Lookup (Faculty)
    2. Dense FAISS Search (Top 10)
    3. Sparse BM25 Search (Top 10)
    4. Cross-Encoder Re-Ranking & Top-k Selection
    """
    logger.info(f"[RAG] Retrieving for query: {query!r}")

    # 1. Structured matches
    faculty_docs = find_faculty_matches(query)

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

    if not candidate_indices and not faculty_docs:
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
    top_docs: List[Document] = list(faculty_docs)
    seen_contents = {d.page_content for d in top_docs}

    for score, item in scored_candidates:
        if len(top_docs) >= k:
            break
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
