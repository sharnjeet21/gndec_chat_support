#!/usr/bin/env python3
"""Rebuild gold_set_500.jsonl with proper JSONL format and verified ground truths."""
import json, os

BASE = "/home/sharnjeet-singh/Developer/gndec_rag"
gold_path = os.path.join(BASE, "data/gold_set_500.jsonl")

# Current file is corrupted (JSON array from Write tool)
# Try to read it
try:
    with open(gold_path) as f:
        content = f.read()
    if content.startswith("["):
        print("File is JSON array format - rebuilding from scratch")
        # It's a JSON array - read it
        data = json.loads(content)
        if isinstance(data, list):
            print(f"Loaded {len(data)} entries from JSON array")
            gold = data
        else:
            gold = []
    else:
        gold = [json.loads(line) for line in open(gold_path)]
        print(f"Loaded {len(gold)} entries as JSONL")
except Exception as e:
    print(f"Error: {e}")
    gold = []

# Verified fee amounts from gndec.ac.in/?q=node/572 (2024-25 official)
VERIFIED_FEES = {
    "GOLD-FEE-001": {"key_facts": ["67929", "87229", "84829", "30429", "49729", "47329", "19300", "16900"], "must_contain_tables": True, "prohibited": ["I do not have information"], "should_abstain": False},
    "GOLD-FEE-002": {"key_facts": ["67929", "B.Tech"], "must_contain_tables": True, "prohibited": [], "should_abstain": False},
    "GOLD-FEE-003": {"key_facts": ["84829", "30429", "TFW"], "must_contain_tables": True, "prohibited": [], "should_abstain": False},
    "GOLD-FEE-004": {"key_facts": ["49729", "47329", "PMS"], "must_contain_tables": True, "prohibited": [], "should_abstain": False},
    "GOLD-FEE-005": {"key_facts": ["60339", "M.Tech"], "must_contain_tables": True, "prohibited": [], "should_abstain": False},
    "GOLD-FEE-006": {"key_facts": ["63339", "18720", "MBA", "MCA"], "must_contain_tables": True, "prohibited": [], "should_abstain": False},
    "GOLD-FEE-007": {"key_facts": ["19300", "18720"], "must_contain_tables": True, "prohibited": [], "should_abstain": False},
    "GOLD-FEE-008": {"key_facts": ["16900", "B.Tech"], "must_contain_tables": True, "prohibited": [], "should_abstain": False},
    "GOLD-FEE-009": {"key_facts": ["B.Voc", "BBA", "BCA"], "must_contain_tables": True, "prohibited": [], "should_abstain": False},
    "GOLD-FEE-010": {"key_facts": ["67929", "B.Tech"], "must_contain_tables": True, "prohibited": [], "should_abstain": False},
}

updated = 0
for entry in gold:
    gid = entry.get("id", "")
    if gid in VERIFIED_FEES:
        entry["ground_truth"] = VERIFIED_FEES[gid]
        updated += 1

print(f"Updated {updated} fee ground truths")

# Write as proper JSONL
with open(gold_path, "w") as f:
    for entry in gold:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

size = os.path.getsize(gold_path)
print(f"Written {size} bytes, {len(gold)} entries to gold_set_500.jsonl")

# Summary
categories = {}
for entry in gold:
    cat = entry.get("category", "Unknown")
    categories[cat] = categories.get(cat, 0) + 1
for cat, count in sorted(categories.items()):
    print(f"  {cat}: {count}")
