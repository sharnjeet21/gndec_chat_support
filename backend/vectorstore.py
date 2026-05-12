# backend/vectorstore.py
import os
import json
import faiss
import logging
from typing import List, Dict, Any

import numpy as np
from sentence_transformers import SentenceTransformer
from langchain.docstore.document import Document
from langchain.vectorstores import FAISS as LC_FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.docstore import InMemoryDocstore

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

with open(META_PATH, "r") as f:
    META: List[Dict[str, Any]] = json.load(f)

# Embeddings
MODEL_NAME = "all-MiniLM-L6-v2"
logging.info(f"Loading embedding model: {MODEL_NAME}")
embed_model = SentenceTransformer(MODEL_NAME)
lc_embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME)

index_to_docstore_id = {i: str(i) for i in range(faiss_index.ntotal)}

docstore = InMemoryDocstore({})  # we don’t store full docs here

vectorstore = LC_FAISS(
    embedding_function=lc_embeddings,
    index=faiss_index,
    docstore=docstore,
    index_to_docstore_id=index_to_docstore_id,
)


def metadata_to_doc(item: Dict[str, Any]) -> Document:
    """Convert metadata record into LangChain Document"""
    text = f"Q: {item['question']}\nA: {item['answer']}\nSection: {item['section']}"
    return Document(page_content=text, metadata=item)


def get_retriever(k: int = 3):
    """LangChain-compatible retriever using FAISS index"""

    def retrieve(query: str) -> List[Document]:
        logging.info(f"[RAG] Searching FAISS for query={query!r}")

        # Manual FAISS search for logging + domain guard compatibility
        query_vec = embed_model.encode([query], convert_to_numpy=True).astype("float32")
        scores, ids = faiss_index.search(query_vec, k)

        docs = []
        for rank, (idx, score) in enumerate(zip(ids[0], scores[0])):
            if idx < 0:
                continue
            item = META[int(idx)]
            logging.info(
                f"   #{rank+1} Score={score:.4f} | "
                f"Q={item['question']!r} | File={item['source_file']}"
            )
            docs.append(metadata_to_doc(item))

        return docs

    return retrieve


def similarity_search(query: str, k: int = 3) -> List[Document]:
    """LangChain-style wrapper for pipelines needing retriever with LC API"""
    docs = get_retriever(k)(query)
    return docs


retriever = get_retriever(k=3)
