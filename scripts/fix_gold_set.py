#!/usr/bin/env python3
"""Fix gold_set_500.jsonl with verified ground truths."""
import json, os

# Load gold set
try:
    gold = [json.loads(line) for line in open("data/gold_set_500.jsonl")]
    print(f"Loaded {len(gold)} gold cases")
except:
    gold = []
    print("Could not load gold_set_500.jsonl")

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

# Write updated gold set
with open("data/gold_set_500.jsonl", "w") as f:
    for entry in gold:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

size = os.path.getsize("data/gold_set_500.jsonl")
print(f"Written {size} bytes, {len(gold)} entries to gold_set_500.jsonl")

# Summary
categories = {}
for entry in gold:
    cat = entry.get("category", "Unknown")
    categories[cat] = categories.get(cat, 0) + 1
for cat, count in sorted(categories.items()):
    print(f"  {cat}: {count}")
