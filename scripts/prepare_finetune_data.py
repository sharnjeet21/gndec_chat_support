"""
scripts/prepare_finetune_data.py — Prepare Domain Contrastive Training Dataset
=============================================================================
Extracts (question, positive_passage) pairs from curated GNDEC knowledge bases
to fine-tune domain embeddings for higher Hit@k retrieval accuracy.

Run:
    python3 scripts/prepare_finetune_data.py
"""

import os
import json
import random

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")
TRAIN_OUT = os.path.join(DATA_DIR, "train_pairs.jsonl")
VAL_OUT = os.path.join(DATA_DIR, "val_pairs.jsonl")

# Prioritized sources (curated facts have higher domain density)
SOURCES = [
    "gndec_facts.json",
    "faculty.json",
    "syllabi.json",
    "tnp_data.json",
    "notices.json",
    "datesheets.json",
    "external_facts.json",
    "fee_structures.json",
    "courses_offered.json",
]

def load_pairs():
    pairs = []
    seen = set()

    for src in SOURCES:
        path = os.path.join(DATA_DIR, src)
        if not os.path.exists(path):
            continue

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        if src == "faculty.json":
            for item in data:
                name = item.get("name", "").strip()
                dept = item.get("department", "").strip()
                desig = item.get("designation", "").strip()
                email = item.get("email", "").strip()
                if not name:
                    continue
                q = f"Who is {name}? What is the contact email and designation for {name} in {dept}?"
                a = f"{name} is a {desig} in the {dept} department at GNDEC. You can contact them via email at {email}."
                pairs.append({"anchor": q, "positive": a, "source": src})
                count += 1
        elif src == "syllabi.json":
            for item in data:
                title = item.get("title", "").strip()
                content = item.get("content", "").strip()
                if not content or len(content) < 30:
                    continue
                q = f"What is the syllabus, scheme, or notice for {title}?"
                pairs.append({"anchor": q, "positive": content[:800], "source": src})
                count += 1
        else:
            for item in data:
                q = (item.get("question") or "").strip()
                a = (item.get("answer") or "").strip()

                # Filter trivial or noisy entries
                if len(q) < 12 or len(a) < 25:
                    continue

                # Deduplicate by anchor
                key = (q.lower(), a[:60].lower())
                if key in seen:
                    continue
                seen.add(key)

                pairs.append({
                    "anchor": q,
                    "positive": a[:800],  # Keep relevant top passage
                    "source": src
                })
                count += 1

        print(f"Loaded {count:>5} high-quality pairs from {src}")

    # Also sample clean entries from gndec_data.json
    gndec_data_path = os.path.join(DATA_DIR, "gndec_data.json")
    if os.path.exists(gndec_data_path):
        with open(gndec_data_path, "r", encoding="utf-8") as f:
            scraped = json.load(f)
        scraped_count = 0
        for item in scraped:
            q = (item.get("question") or "").strip()
            a = (item.get("answer") or "").strip()
            if len(q) < 15 or len(a) < 40 or len(a) > 2000:
                continue
            key = (q.lower(), a[:60].lower())
            if key in seen:
                continue
            seen.add(key)
            pairs.append({
                "anchor": q,
                "positive": a[:800],
                "source": "gndec_data.json"
            })
            scraped_count += 1
            if scraped_count >= 5000:  # Bound to top 5000 clean pairs to balance curated facts
                break
        print(f"Loaded {scraped_count:>5} sampled pairs from gndec_data.json")

    return pairs

def main():
    pairs = load_pairs()
    print(f"\nTotal contrastive pairs prepared: {len(pairs)}")

    random.seed(42)
    random.shuffle(pairs)

    val_size = max(100, int(len(pairs) * 0.1))
    val_set = pairs[:val_size]
    train_set = pairs[val_size:]

    with open(TRAIN_OUT, "w", encoding="utf-8") as f:
        for p in train_set:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    with open(VAL_OUT, "w", encoding="utf-8") as f:
        for p in val_set:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"✅ Training set saved to {TRAIN_OUT} ({len(train_set)} pairs)")
    print(f"✅ Validation set saved to {VAL_OUT} ({len(val_set)} pairs)")

if __name__ == "__main__":
    main()
