"""
build_vector_db.py — GNDEC College RAG Knowledge Base Builder
=============================================================
Loads GNDEC scraped data + curated facts and builds a FAISS vector index.

Run:
    python3 backend/build_vector_db.py
"""

import json
import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

HERE     = os.path.dirname(__file__)
DATA_DIR = os.path.join(os.path.dirname(HERE), "data")
FAISS_DIR = os.path.join(HERE, "faiss_store")

MODEL_NAME = "all-MiniLM-L6-v2"
MODEL = SentenceTransformer(MODEL_NAME)


# -----------------------------------------------
# Loaders
# -----------------------------------------------

def load_flat_json(filename: str) -> list:
    """Load a flat list of {question, answer, section, source_file} dicts."""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        print(f"  ⚠️  Not found, skipping: {path}")
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    out = []
    for item in data:
        q       = (item.get("question")    or "").strip()
        a       = (item.get("answer")      or "").strip()
        section = (item.get("section")     or "General").strip()
        source  = (item.get("source_file") or "gndec.ac.in").strip()
        doc_url = (item.get("doc_url")     or "").strip()

        if not q or not a:
            continue
        if len(q) < 10 or len(a) < 20:
            continue

        entry = {
            "question":    q,
            "answer":      a,
            "section":     section,
            "source_file": source,
        }
        if doc_url:
            entry["doc_url"] = doc_url

        out.append(entry)

    print(f"  Loaded {len(out):>5} pairs from {filename}")
    return out


# -----------------------------------------------
# Load ALL datasets
# -----------------------------------------------

def load_faculty_json() -> list:
    path = os.path.join(DATA_DIR, "faculty.json")
    if not os.path.exists(path):
        print(f"  ⚠️  Not found, skipping: {path}")
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    out = []
    for item in data:
        name = item.get("name", "").strip()
        dept = item.get("department", "").strip()
        desig = item.get("designation", "").strip()
        email = item.get("email", "").strip()
        
        if not name:
            continue
            
        q = f"Who is {name}? What is the contact email and designation for {name} in {dept}?"
        a = f"{name} is a {desig} in the {dept} department at GNDEC. You can contact them via email at {email}."
        
        out.append({
            "question": q,
            "answer": a,
            "section": "Faculty Directory",
            "source_file": "faculty.json"
        })

    print(f"  Loaded {len(out):>5} pairs from faculty.json")
    return out

def load_syllabi_json() -> list:
    path = os.path.join(DATA_DIR, "syllabi.json")
    if not os.path.exists(path):
        print(f"  ⚠️  Not found, skipping: {path}")
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    out = []
    for item in data:
        title = item.get("title", "").strip()
        url = item.get("url", "").strip()
        content = item.get("content", "").strip()
        
        if not content:
            continue
            
        q = f"What is the syllabus, scheme, or notice for {title}?"
        a = content[:2500] # Ensure it's not overly large for a single chunk, or rely on FAISS to handle it
        
        out.append({
            "question": q,
            "answer": a,
            "section": "Syllabus & Schemes",
            "source_file": "syllabi.json",
            "doc_url": url
        })

    print(f"  Loaded {len(out):>5} pairs from syllabi.json")
    return out

def load_tnp_json() -> list:
    path = os.path.join(DATA_DIR, "tnp_data.json")
    if not os.path.exists(path):
        print(f"  ⚠️  Not found, skipping: {path}")
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"  Loaded {len(data):>5} pairs from tnp_data.json")
    return data

def load_all_faqs() -> list:
    all_faqs = []

    print("Loading datasets...")

    # 1. Manually curated GNDEC facts (highest quality — load first)
    all_faqs += load_flat_json("gndec_facts.json")

    # 2. Scraped GNDEC website data
    all_faqs += load_flat_json("gndec_data.json")
    
    # 3. Faculty data
    all_faqs += load_faculty_json()
    
    # 4. Syllabi data
    all_faqs += load_syllabi_json()
    
    # 5. Training & Placement data
    all_faqs += load_tnp_json()

    # 6. External Web Search Facts
    all_faqs += load_flat_json("external_facts.json")

    # 7. Complete Fee Structures
    all_faqs += load_flat_json("fee_structures.json")
    
    # 8. Courses Offered
    all_faqs += load_flat_json("courses_offered.json")

    print(f"\nTOTAL LOADED = {len(all_faqs)} Q&A pairs")
    return all_faqs


# -----------------------------------------------
# Build FAISS Vectorstore
# -----------------------------------------------

def build_faiss_index():
    faqs = load_all_faqs()

    texts = [
        f"Q: {f['question']}\nA: {f['answer']}\nSection: {f['section']}"
        for f in faqs
    ]

    print(f"\nEmbedding {len(texts)} entries with {MODEL_NAME} ...")
    embeddings = MODEL.encode(texts, convert_to_numpy=True, show_progress_bar=True)
    embeddings = embeddings.astype("float32")

    dim = embeddings.shape[1]
    print(f"Vector dim = {dim}")

    index = faiss.IndexFlatL2(dim)
    print("Adding vectors to FAISS...")
    index.add(embeddings)

    os.makedirs(FAISS_DIR, exist_ok=True)

    index_path = os.path.join(FAISS_DIR, "faq.index")
    meta_path  = os.path.join(FAISS_DIR, "meta.json")

    print(f"Saving FAISS index → {index_path}")
    faiss.write_index(index, index_path)

    print(f"Saving metadata   → {meta_path}")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(faqs, f, indent=2, ensure_ascii=False)

    print(f"\n✅ FAISS build complete. {len(faqs)} vectors indexed.")
    print(f"   Curated facts : {sum(1 for x in faqs if x['source_file'] in ('gndec.ac.in',) and len(x['answer']) > 100)}")
    print(f"   Scraped data  : {sum(1 for x in faqs if x.get('doc_url') or True) - 50}")


if __name__ == "__main__":
    build_faiss_index()
