# backend/vectorstore.py
import os
import json
import faiss
import logging
from typing import List, Dict, Any

import numpy as np
from sentence_transformers import SentenceTransformer
from langchain.docstore.document import Document
from langchain_community.retrievers import BM25Retriever

logging.basicConfig(level=logging.INFO)

# Paths
HERE = os.path.dirname(os.path.abspath(__file__))
FAISS_DIR = os.path.join(HERE, "faiss_store")
INDEX_PATH = os.path.join(FAISS_DIR, "faq.index")
META_PATH = os.path.join(FAISS_DIR, "meta.json")

if not os.path.exists(INDEX_PATH) or not os.path.exists(META_PATH):
    raise RuntimeError(
        f"FAISS index or meta.json missing!\n" f"Run: python backend/build_vector_db.py"
    )

logging.info("🔄 Loading FAISS index & metadata...")
faiss_index = faiss.read_index(INDEX_PATH)

with open(META_PATH, "r", encoding="utf-8") as f:
    META: List[Dict[str, Any]] = json.load(f)

# Embeddings
MODEL_NAME = "all-MiniLM-L6-v2"
logging.info(f"Loading embedding model: {MODEL_NAME} on CPU to avoid MPS crash")
embed_model = SentenceTransformer(MODEL_NAME, device="cpu")


def metadata_to_doc(item: Dict[str, Any]) -> Document:
    """Convert metadata record into LangChain Document"""
    text = f"Q: {item['question']}\nA: {item['answer']}\nSection: {item['section']}"
    return Document(page_content=text, metadata=item)


logging.info("🔄 Building BM25 keyword index...")
all_docs = [metadata_to_doc(item) for item in META]
bm25_retriever = BM25Retriever.from_documents(all_docs)


def get_retriever(k: int = 3):
    """LangChain-compatible retriever using FAISS + BM25 Hybrid Search (Reciprocal Rank Fusion)"""

    def retrieve(query: str) -> List[Document]:
        logging.info(f"[RAG] Searching FAISS+BM25 Hybrid for query={query!r}")

        # 1. FAISS Search
        query_vec = embed_model.encode([query], convert_to_numpy=True).astype("float32")
        scores, ids = faiss_index.search(query_vec, k)
        
        docs_faiss = []
        for rank, (idx, score) in enumerate(zip(ids[0], scores[0])):
            if idx < 0 or score > 1.4:
                if idx >= 0:
                    logging.info(f"   [FAISS] #{rank+1} Score={score:.4f} (SKIPPED > 1.4) | Q={META[int(idx)]['question']!r}")
                continue
            item = META[int(idx)]
            logging.info(f"   [FAISS] #{rank+1} Score={score:.4f} | Q={item['question']!r}")
            docs_faiss.append(metadata_to_doc(item))

        # 2. BM25 Search
        bm25_retriever.k = k
        docs_bm25 = bm25_retriever.invoke(query)
        for rank, doc in enumerate(docs_bm25):
            logging.info(f"   [BM25]  #{rank+1} | Q={doc.metadata.get('question', '')!r}")

        # 3. Reciprocal Rank Fusion (RRF)
        # Weights: FAISS 0.6, BM25 0.4
        rrf_scores = {}
        doc_map = {}
        
        for rank, doc in enumerate(docs_faiss):
            key = doc.page_content
            rrf_scores[key] = rrf_scores.get(key, 0) + (1.0 / (rank + 60)) * 0.6
            doc_map[key] = doc
            
        for rank, doc in enumerate(docs_bm25):
            key = doc.page_content
            rrf_scores[key] = rrf_scores.get(key, 0) + (1.0 / (rank + 60)) * 0.4
            doc_map[key] = doc
            
        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        final_docs = [doc_map[key] for key, _ in sorted_docs[:k]]
        
        logging.info(f"   [HYBRID] Returned top {len(final_docs)} merged documents.")
        return final_docs

    return retrieve


def similarity_search(query: str, k: int = 3) -> List[Document]:
    """LangChain-style wrapper for pipelines needing retriever with LC API"""
    docs = get_retriever(k)(query)
    return docs


retriever = get_retriever(k=8)
