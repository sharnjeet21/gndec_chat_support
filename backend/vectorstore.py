# backend/vectorstore.py
import os
import json
import faiss
import logging
from typing import List, Dict, Any

from sentence_transformers import SentenceTransformer
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever

logging.basicConfig(level=logging.INFO)

# Paths
HERE = os.path.dirname(os.path.abspath(__file__))
FAISS_DIR = os.path.join(HERE, "faiss_store")
INDEX_PATH = os.path.join(FAISS_DIR, "faq.index")
META_PATH = os.path.join(FAISS_DIR, "meta.json")

if not os.path.exists(INDEX_PATH) or not os.path.exists(META_PATH):
    raise RuntimeError(
        f"FAISS index or meta.json missing!\nRun: python backend/build_vector_db.py"
    )

logging.info("🔄 Loading FAISS index & metadata...")
faiss_index = faiss.read_index(INDEX_PATH)

with open(META_PATH, "r", encoding="utf-8") as f:
    META: List[Dict[str, Any]] = json.load(f)

# Embeddings
MODEL_NAME = "all-MiniLM-L6-v2"
logging.info(f"Loading embedding model: {MODEL_NAME} on CPU")
embed_model = SentenceTransformer(MODEL_NAME, device="cpu")


def metadata_to_doc(item: Dict[str, Any]) -> Document:
    """Convert metadata record into LangChain Document"""
    text = f"Q: {item['question']}\nA: {item['answer']}\nSection: {item['section']}"
    return Document(page_content=text, metadata=item)


logging.info("🔄 Building BM25 keyword index...")
# Only build BM25 for non-fee documents, as fee docs (26k+) make startup take 10+ minutes
bm25_meta = [item for item in META if item.get('source_file') != 'fee_structures.json']
all_docs = [metadata_to_doc(item) for item in bm25_meta]
bm25_retriever = BM25Retriever.from_documents(all_docs)


class FaissRetriever(BaseRetriever):
    """Custom LangChain retriever wrapping CPU FAISS index."""
    k: int = 10
    min_score: float = 0.35

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        query_vec = embed_model.encode([query], convert_to_numpy=True).astype("float32")
        faiss.normalize_L2(query_vec)
        scores, ids = faiss_index.search(query_vec, self.k)

        docs = []
        for idx, l2_score in zip(ids[0], scores[0]):
            cosine_sim = max(-1.0, min(1.0, 1.0 - (float(l2_score) ** 2) / 2.0))
            if idx >= 0 and cosine_sim >= self.min_score:
                docs.append(metadata_to_doc(META[int(idx)]))
        return docs


faiss_retriever = FaissRetriever(k=10, min_score=0.35)
bm25_retriever.k = 10
ensemble_retriever = EnsembleRetriever(
    retrievers=[faiss_retriever, bm25_retriever],
    weights=[0.5, 0.5]
)


def get_retriever(k: int = 8):
    """LangChain EnsembleRetriever (FAISS + BM25 with RRF)"""
    def retrieve(query: str) -> List[Document]:
        logging.info(f"[RAG] Searching FAISS+BM25 Ensemble for query={query!r}")
        return ensemble_retriever.invoke(query)[:k]

    return retrieve


retriever = get_retriever(k=8)
