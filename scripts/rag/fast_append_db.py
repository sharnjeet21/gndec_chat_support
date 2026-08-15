import json
import os
import faiss
from sentence_transformers import SentenceTransformer

HERE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
FAISS_DIR = os.path.join(HERE, "backend", "faiss_store")
INDEX_PATH = os.path.join(FAISS_DIR, "faq.index")
META_PATH = os.path.join(FAISS_DIR, "meta.json")
COURSES_PATH = os.path.join(HERE, "data", "courses_offered.json")

print("Loading existing FAISS index...")
index = faiss.read_index(INDEX_PATH)

print("Loading existing meta.json...")
with open(META_PATH, "r", encoding="utf-8") as f:
    meta = json.load(f)

print("Loading courses_offered.json...")
with open(COURSES_PATH, "r", encoding="utf-8") as f:
    courses = json.load(f)

print("Formatting texts...")
texts = []
for c in courses:
    text = f"Q: {c['question']}\nA: {c['answer']}\nSection: {c.get('section', 'General')}"
    texts.append(text)
    meta.append(c)

print("Loading embedding model on CPU...")
model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")

print("Embedding...")
embeddings = model.encode(texts, convert_to_numpy=True).astype("float32")

print("Adding to FAISS...")
index.add(embeddings)

print("Saving FAISS index...")
faiss.write_index(index, INDEX_PATH)

print("Saving meta.json...")
with open(META_PATH, "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2, ensure_ascii=False)

print("✅ Successfully appended and saved!")
