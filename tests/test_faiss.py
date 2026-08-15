import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL = SentenceTransformer("all-MiniLM-L6-v2")
index = faiss.read_index("backend/faiss_store/faq.index")

with open("backend/faiss_store/meta.json", "r") as f:
    meta = json.load(f)

questions = [
    "What is the B.Tech fee structure?",
    "Are there any seats reserved for rural or Sikh minority students?",
    "What are the cutoff ranks for B.Tech admission?"
]

for q in questions:
    print(f"\n======================================")
    print(f"QUERY: {q}")
    print(f"======================================")
    
    vec = MODEL.encode([q], convert_to_numpy=True).astype("float32")
    distances, indices = index.search(vec, 3)
    
    for i, idx in enumerate(indices[0]):
        if idx < len(meta):
            m = meta[idx]
            print(f"\n--- Result {i+1} ---")
            print(f"Source: {m.get('source_file')} | URL: {m.get('doc_url', 'N/A')}")
            print(f"Content: Q: {m.get('question')}\nA: {m.get('answer')}")

