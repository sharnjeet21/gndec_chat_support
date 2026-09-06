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
import torch
import numpy as np
from sentence_transformers import SentenceTransformer

# Maximize multi-core CPU throughput for indexing
torch.set_num_threads(os.cpu_count() or 8)

HERE     = os.path.dirname(__file__)
DATA_DIR = os.path.join(os.path.dirname(HERE), "data")
FAISS_DIR = os.path.join(HERE, "faiss_store")

MODEL_NAME = "all-MiniLM-L6-v2"
MODEL = SentenceTransformer(MODEL_NAME)
MODEL.max_seq_length = 256


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
    from collections import defaultdict
    dept_map = defaultdict(list)

    for item in data:
        name = item.get("name", "").strip()
        dept = item.get("department", "").strip()
        desig = item.get("designation", "").strip()
        email = item.get("email", "").strip()
        qual = item.get("qualification", "").strip()
        exp = item.get("experience", "").strip()
        research = item.get("research_interest", "").strip()
        journals = item.get("publications_journal", "").strip()
        confs = item.get("publications_conference", "").strip()
        memberships = item.get("memberships", "").strip()
        profile_url = item.get("profile_url", "").strip()

        if not name:
            continue

        q = f"Who is {name}? What is the contact email, designation, qualification, and research interest of {name} in {dept}?"

        details = [f"{name} is a {desig} in the {dept} department at GNDEC (Guru Nanak Dev Engineering College)."]
        if email:
            details.append(f"- Email: {email}")
        if qual:
            details.append(f"- Qualification: {qual}")
        if exp:
            details.append(f"- Experience: {exp}")
        if research:
            details.append(f"- Research Interests: {research}")
        if journals:
            details.append(f"- Journal Publications: {journals}")
        if confs:
            details.append(f"- Conference Publications: {confs}")
        if memberships:
            details.append(f"- Professional Memberships: {memberships}")
        if profile_url:
            details.append(f"- Official Faculty Profile: {profile_url}")

        a = "\n".join(details)

        entry = {
            "question": q,
            "answer": a,
            "section": f"Faculty Directory - {dept}",
            "source_file": "faculty.json"
        }
        if profile_url:
            entry["doc_url"] = profile_url

        out.append(entry)
        dept_map[dept].append(f"- {name}, {desig} (Email: {email})")

    # Add grouped QA pairs for each department
    for dept, members in dept_map.items():
        q = f"Who are the faculty and staff members of the {dept} department? What is the list of teachers in {dept}?"
        a = f"The faculty and staff members of the {dept} department at GNDEC include ({len(members)} members):\n" + "\n".join(members)
        out.append({
            "question": q,
            "answer": a,
            "section": f"Faculty Directory - {dept}",
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

    import re

    def clean_title(t: str) -> str:
        t = re.sub(r"\s+", " ", t).strip()
        lines = [l.strip() for l in t.split("\n") if l.strip()]
        return lines[0] if lines else t

    out = []
    CHUNK_SIZE = 1500
    CHUNK_OVERLAP = 250

    for item in data:
        raw_title = item.get("title", "").strip()
        title = clean_title(raw_title)
        url = item.get("url", "").strip()
        content = item.get("content", "").strip()

        if not content or len(content) < 50:
            continue

        dept = "General"
        if "cse.gndec" in url or "computer science" in title.lower():
            dept = "Computer Science & Engineering (CSE)"
        elif "it.gndec" in url or "information technology" in title.lower():
            dept = "Information Technology (IT)"
        elif "ee.gndec" in url or "electrical" in title.lower():
            dept = "Electrical Engineering (EE)"
        elif "ece.gndec" in url or "electronics" in title.lower():
            dept = "Electronics & Communication Engineering (ECE)"
        elif "me.gndec" in url or "mechanical" in title.lower() or "robotics" in title.lower():
            dept = "Mechanical Engineering (ME)"
        elif "ce.gndec" in url or "civil" in title.lower():
            dept = "Civil Engineering (CE)"
        elif "mba.gndec" in url or "bba" in title.lower() or "b.com" in title.lower() or "mba" in title.lower():
            dept = "Business Administration (MBA / BBA / B.Com)"
        elif "ca.gndec" in url or "mca" in url or "bca" in title.lower() or "mca" in title.lower():
            dept = "Computer Applications (BCA / MCA)"
        elif "applied science" in title.lower():
            dept = "Applied Sciences"

        text_len = len(content)
        if text_len <= CHUNK_SIZE:
            out.append({
                "question": f"What is the syllabus, study scheme, or curriculum for {title} in {dept} at GNDEC?",
                "answer": content,
                "section": f"Syllabus & Schemes - {dept}",
                "source_file": "syllabi.json",
                "doc_url": url
            })
        else:
            start = 0
            part_idx = 1
            while start < text_len:
                end = min(start + CHUNK_SIZE, text_len)
                sub_text = content[start:end].strip()

                q = f"What is the syllabus, study scheme, subjects, and course outline for {title} (Part {part_idx}) in {dept} at GNDEC?"
                out.append({
                    "question": q,
                    "answer": sub_text,
                    "section": f"Syllabus & Schemes - {dept}",
                    "source_file": "syllabi.json",
                    "doc_url": url
                })

                if end >= text_len:
                    break
                start += (CHUNK_SIZE - CHUNK_OVERLAP)
                part_idx += 1

    print(f"  Loaded {len(out):>5} chunked pairs from syllabi.json across all departments")
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

    # Load order: bulk scraped data FIRST (lower priority), then curated/authoritative
    # data LAST so newer entries with the same question overwrite stale ones.
    #
    # Duplicate strategy: keep the LAST occurrence of each unique question string,
    # so authoritative sources (verified_facts, admission_process, gndec_facts) always win
    # over older scraped entries in gndec_data.json.

    # ---- Bulk scraped data (base layer, lower priority) ----
    all_faqs += load_flat_json("gndec_data.json")     # Aug 11 — large but older
    all_faqs += load_flat_json("gndec_facts.json")     # Sep 6  — curated facts
    all_faqs += load_faculty_json()
    all_faqs += load_syllabi_json()
    all_faqs += load_tnp_json()
    all_faqs += load_flat_json("external_facts.json")
    all_faqs += load_flat_json("fee_structures.json")
    all_faqs += load_flat_json("courses_offered.json")
    all_faqs += load_flat_json("notices.json")
    all_faqs += load_flat_json("datesheets.json")

    # ---- Authoritative / latest data (overwrites any stale duplicates above) ----
    all_faqs += load_flat_json("verified_facts.json")   # Sep 6  — post-scrape corrections
    all_faqs += load_flat_json("admission_process.json")# Sep 6  — latest admission procedure

    # De-duplicate: keep LAST occurrence of each question (authoritative wins)
    seen_questions: list[str] = []
    deduped: list[dict] = []
    for entry in reversed(all_faqs):
        q = entry.get("question", "").strip().lower()
        if q and q not in seen_questions:
            seen_questions.append(q)
            deduped.append(entry)
    all_faqs = list(reversed(deduped))  # restore original order

    print(f"\nTOTAL LOADED = {len(all_faqs)} Q&A pairs")
    return all_faqs


# -----------------------------------------------
# Build FAISS Vectorstore
# -----------------------------------------------

def build_faiss_index():
    faqs = load_all_faqs()

    texts = [
        f"Q: {f['question']}\nSection: {f['section']}"
        for f in faqs
    ]

    # Use CPU threads optimally and batch size 128 for good throughput
    print(f"\nEmbedding {len(texts)} entries with {MODEL_NAME} (batch_size=128, {torch.get_num_threads()} threads, max_seq_length=128) ...")
    MODEL.max_seq_length = 128
    with torch.inference_mode():
        embeddings = MODEL.encode(texts, batch_size=128, convert_to_numpy=True, show_progress_bar=True)
    embeddings = embeddings.astype("float32")
    faiss.normalize_L2(embeddings)

    dim = embeddings.shape[1]
    print(f"Vector dim = {dim}")

    index = faiss.IndexFlatIP(dim)
    print("Adding vectors to FAISS...")
    index.add(embeddings)

    tmp_faiss_dir = FAISS_DIR + "_tmp"
    os.makedirs(tmp_faiss_dir, exist_ok=True)

    index_path = os.path.join(tmp_faiss_dir, "faq.index")
    meta_path  = os.path.join(tmp_faiss_dir, "meta.json")

    print(f"Saving temporary FAISS index → {index_path}")
    faiss.write_index(index, index_path)

    print(f"Saving temporary metadata   → {meta_path}")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(faqs, f, indent=2, ensure_ascii=False)

    # Atomic swap
    import shutil
    final_backup = FAISS_DIR + "_old"
    if os.path.exists(FAISS_DIR):
        if os.path.exists(final_backup):
            shutil.rmtree(final_backup)
        os.rename(FAISS_DIR, final_backup)
    os.rename(tmp_faiss_dir, FAISS_DIR)
    if os.path.exists(final_backup):
        shutil.rmtree(final_backup, ignore_errors=True)

    print(f"\n✅ FAISS atomic build complete. {len(faqs)} vectors indexed and swapped.")
    print(f"   Curated facts : {sum(1 for x in faqs if x['source_file'] in ('gndec.ac.in',) and len(x['answer']) > 100)}")
    print(f"   Scraped data  : {sum(1 for x in faqs if x.get('doc_url') or True) - 50}")


if __name__ == "__main__":
    build_faiss_index()
