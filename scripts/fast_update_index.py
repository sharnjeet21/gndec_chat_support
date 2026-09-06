#!/usr/bin/env python3
"""
fast_update_index.py — Lightning-fast FAISS index updater
Reconstructs existing non-faculty vectors and encodes only updated/new documents.
"""

import json
import os
import faiss
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(HERE)
FAISS_DIR = os.path.join(ROOT, "backend", "faiss_store")
META_PATH = os.path.join(FAISS_DIR, "meta.json")
INDEX_PATH = os.path.join(FAISS_DIR, "faq.index")

from backend.build_vector_db import load_faculty_json

def fast_update():
    print("=" * 80)
    print("FAST RE-INDEXING UPDATED FACULTY DIRECTORY INTO FAISS STORE")
    print("=" * 80)

    # 1. Load existing metadata and FAISS index
    with open(META_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    index = faiss.read_index(INDEX_PATH)
    total = index.ntotal
    print(f"Loaded existing index with {total} vectors and {len(meta)} metadata items.")

    # 2. Separate non-faculty and faculty indices
    keep_indices = []
    keep_meta = []
    for i, m in enumerate(meta):
        if m.get("source_file") != "faculty.json":
            keep_indices.append(i)
            keep_meta.append(m)

    print(f"Preserving {len(keep_indices)} non-faculty vectors from existing store.")

    # 3. Extract vectors to keep using fast bulk reconstruction
    keep_vectors = []
    for idx in keep_indices:
        keep_vectors.append(index.reconstruct(idx))
    keep_vectors = np.array(keep_vectors, dtype=np.float32)
    print(f"Preserved vector array shape: {keep_vectors.shape}")

    # 4. Load new rich faculty data
    new_faculty_qa = load_faculty_json()
    print(f"Encoding {len(new_faculty_qa)} new faculty documents with full details...")

    model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    model.max_seq_length = 256

    texts = [f"Q: {f['question']}\nA: {f['answer']}\nSection: {f['section']}" for f in new_faculty_qa]
    new_embeddings = model.encode(texts, batch_size=32, convert_to_numpy=True, show_progress_bar=True)
    new_embeddings = new_embeddings.astype(np.float32)
    faiss.normalize_L2(new_embeddings)

    # 5. Combine preserved vectors and new vectors
    all_vectors = np.vstack([keep_vectors, new_embeddings])
    faiss.normalize_L2(all_vectors)

    all_meta = keep_meta + new_faculty_qa

    # 6. Create clean new IndexFlatIP
    dim = all_vectors.shape[1]
    new_index = faiss.IndexFlatIP(dim)
    new_index.add(all_vectors)

    print(f"New index created with {new_index.ntotal} vectors.")

    # 7. Save updated index and metadata
    faiss.write_index(new_index, INDEX_PATH)
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(all_meta, f, indent=2, ensure_ascii=False)

    print(f"✅ Successfully wrote updated index ({INDEX_PATH}) and metadata ({META_PATH}).")

if __name__ == "__main__":
    fast_update()
