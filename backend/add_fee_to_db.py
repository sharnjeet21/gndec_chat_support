import json
import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

HERE = os.path.dirname(__file__)
FAISS_DIR = os.path.join(HERE, "faiss_store")
DATA_DIR = os.path.join(os.path.dirname(HERE), "data")
MODEL_NAME = "all-MiniLM-L6-v2"
MODEL = SentenceTransformer(MODEL_NAME)

index_path = os.path.join(FAISS_DIR, "faq.index")
meta_path  = os.path.join(FAISS_DIR, "meta.json")

print("Loading existing FAISS index and metadata...")
index = faiss.read_index(index_path)
with open(meta_path, "r", encoding="utf-8") as f:
    meta = json.load(f)

print("Loading fee_structures.json...")
fee_path = os.path.join(DATA_DIR, "fee_structures.json")
with open(fee_path, "r", encoding="utf-8") as f:
    fee_data = json.load(f)

texts = [
    f"Q: {f['question']}\nA: {f['answer']}\nSection: {f['section']}"
    for f in fee_data
]

print(f"Embedding {len(texts)} new entries...")
embeddings = MODEL.encode(texts, convert_to_numpy=True)
embeddings = embeddings.astype("float32")

print("Adding to FAISS index...")
index.add(embeddings)

print("Appending metadata...")
meta.extend(fee_data)

print(f"Saving updated FAISS index to {index_path}...")
faiss.write_index(index, index_path)

print(f"Saving updated metadata to {meta_path}...")
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2, ensure_ascii=False)

print("✅ Success!")
