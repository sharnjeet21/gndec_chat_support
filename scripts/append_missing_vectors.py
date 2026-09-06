import os
import json
import numpy as np
import torch

# Use all available CPU cores for fast batch inference
num_cpus = os.cpu_count() or 8
torch.set_num_threads(num_cpus)
os.environ['OMP_NUM_THREADS'] = str(num_cpus)
os.environ['OPENBLAS_NUM_THREADS'] = str(num_cpus)
os.environ['MKL_NUM_THREADS'] = str(num_cpus)

import faiss
from sentence_transformers import SentenceTransformer
from backend.build_vector_db import load_all_faqs

def append_missing():
    faqs = load_all_faqs()
    meta_path = 'backend/faiss_store/meta.json'
    index_path = 'backend/faiss_store/faq.index'

    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    index = faiss.read_index(index_path)
    existing_keys = {(item.get('question', '').strip().lower(), item.get('source_file', '')) for item in meta}
    missing = [f for f in faqs if (f.get('question', '').strip().lower(), f.get('source_file', '')) not in existing_keys]

    print(f"Found {len(missing)} missing items to index.")
    if not missing:
        print("Everything already indexed!")
        return

    model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
    model.max_seq_length = 128
    texts = [f"Q: {f['question']}\nSection: {f['section']}" for f in missing]
    print(f"Encoding {len(texts)} missing items (batch_size=128, threads={num_cpus})...")
    embeddings = model.encode(texts, batch_size=128, convert_to_numpy=True, show_progress_bar=True)
    embeddings = embeddings.astype(np.float32)
    faiss.normalize_L2(embeddings)

    print(f"Adding {len(embeddings)} vectors to FAISS index...")
    index.add(embeddings)
    meta.extend(missing)

    print(f"Saving updated FAISS index to {index_path}...")
    faiss.write_index(index, index_path)

    print(f"Saving updated metadata to {meta_path}...")
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"✅ Finished! Index now has {index.ntotal} vectors and {len(meta)} metadata items.")

if __name__ == "__main__":
    append_missing()
