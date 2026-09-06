# scripts/eval_harness.py
"""
Automated Evaluation Harness for GNDEC RAG System.
Measures Retrieval Hit@k, Fact Recall, Zero-Hallucination, Abstention, Formatting, and Latency (p50/p95).
Can be run locally or integrated as a CI gate.
"""

import sys
import os
import asyncio
import time
import json
import argparse
import numpy as np
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent import answer_sync
from backend.vectorstore import retrieve

import unicodedata
import re

import logging
logging.basicConfig(level=logging.ERROR)
for name in ["backend.vectorstore", "backend.agent", "backend.llm.llm", "backend.cache", "sentence_transformers", "root"]:
    logging.getLogger(name).setLevel(logging.ERROR)

def load_gold_set(path: str) -> List[Dict[str, Any]]:
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items

def normalize_eval_text(text: str) -> str:
    """Normalizes Unicode NFKC, non-breaking spaces, hyphens, and whitespace."""
    if not text:
        return ""
    t = unicodedata.normalize('NFKC', str(text))
    t = t.replace(' ', ' ').replace(' ', ' ').replace('​', '').replace('﻿', '')
    t = t.replace('‑', '-').replace('‑', '-').replace('–', '-').replace('—', '-')
    t = re.sub(r'\s+', ' ', t)
    # "85 %" and "85%" are the same fact — drop the space before the percent sign
    t = re.sub(r'(\d)\s+%', r'\1%', t)
    return t.strip()

def check_abstention(text: str) -> bool:
    """Checks if the system appropriately abstained or refused."""
    abstain_cues = [
        "only have knowledge about guru nanak dev engineering college",
        "only have knowledge about gndec",
        "i do not have information",
        "not available in the provided",
        "please contact the college",
        "i am sorry, but i only provide information",
        "no specific details are available",
        "does not offer",
        "is not offered",
        "not offered at gndec",
        "not available",
        "is an engineering college",
        "cannot provide",
        "do not possess"
    ]
    t_lower = normalize_eval_text(text).lower()
    return any(cue in t_lower for cue in abstain_cues)

def score_item(res_text: str, retrieved_docs: List[Any], gt: Dict[str, Any]) -> Dict[str, Any]:
    text_norm = normalize_eval_text(res_text)
    text_lower = text_norm.lower()
    key_facts = gt.get("key_facts", [])
    prohibited = gt.get("prohibited", [])
    must_tables = gt.get("must_contain_tables", False)
    should_abstain = gt.get("should_abstain", False)

    # 1. Retrieval Coverage (Hit@k)
    raw_retrieved = " ".join([getattr(d, "page_content", "") for d in retrieved_docs])
    retrieved_text = normalize_eval_text(raw_retrieved).lower()
    retrieval_hits = [f for f in key_facts if normalize_eval_text(f).lower() in retrieved_text]
    retrieval_hit_rate = (len(retrieval_hits) / len(key_facts) * 100.0) if key_facts else 100.0

    # 2. Fact Recall in Generated Answer
    matched_facts = []
    missing_facts = []
    for fact in key_facts:
        f_norm = normalize_eval_text(fact).lower()
        if f_norm in text_lower:
            matched_facts.append(fact)
        else:
            missing_facts.append(fact)

    fact_score = (len(matched_facts) / len(key_facts) * 100.0) if key_facts else 100.0

    # 3. Prohibited Terms / Hallucination Detection
    hallucinations = [p for p in prohibited if normalize_eval_text(p).lower() in text_lower]
    has_hallucination = len(hallucinations) > 0
    zero_hallucination_score = 0.0 if has_hallucination else 100.0

    # 4. Table Formatting
    has_table = ("|" in res_text and "---" in res_text) or ("| Sr No." in res_text) or ("| Course" in res_text)
    table_score = 100.0
    if must_tables and not has_table:
        table_score = 0.0

    # 5. Abstention Evaluation
    did_abstain = check_abstention(res_text)
    if should_abstain:
        abstention_score = 100.0 if (did_abstain or len(matched_facts) > 0) else 0.0
        passed = (zero_hallucination_score == 100.0) and (abstention_score == 100.0)
        composite_accuracy = (zero_hallucination_score * 0.5) + (abstention_score * 0.5)
    else:
        abstention_score = 100.0 if not did_abstain else (50.0 if fact_score > 50 else 0.0)
        passed = (fact_score >= 70.0) and (not has_hallucination) and (table_score == 100.0)
        composite_accuracy = (fact_score * 0.55) + (zero_hallucination_score * 0.25) + (table_score * 0.20)

    return {
        "passed": passed,
        "composite_accuracy": round(composite_accuracy, 1),
        "fact_score": round(fact_score, 1),
        "retrieval_hit_rate": round(retrieval_hit_rate, 1),
        "matched_facts": matched_facts,
        "missing_facts": missing_facts,
        "hallucinations": hallucinations,
        "has_table": has_table,
        "did_abstain": did_abstain,
    }

async def run_evaluation(gold_file: str, max_cases: int = None):
    print("=" * 90)
    print("🎯 GNDEC RAG COMPREHENSIVE BENCHMARK & EVALUATION HARNESS")
    print("=" * 90)

    test_cases = load_gold_set(gold_file)
    if max_cases:
        test_cases = test_cases[:max_cases]

    print(f"Loaded {len(test_cases)} Gold Test Cases from: {gold_file}\n")

    results = []
    category_metrics = {}
    latencies = []
    retrieval_latencies = []

    for idx, tc in enumerate(test_cases, 1):
        t_id = tc["id"]
        cat = tc["category"]
        query = tc["query"]
        gt = tc["ground_truth"]

        print(f"[{idx:02d}/{len(test_cases)}] Testing {t_id} ({cat}): '{query}'")

        # Measure Retrieval separately
        t_ret_0 = time.time()
        try:
            retrieved_docs = retrieve(query, k=6)
            t_ret = round(time.time() - t_ret_0, 3)
        except Exception as e:
            retrieved_docs = []
            t_ret = round(time.time() - t_ret_0, 3)
        retrieval_latencies.append(t_ret)

        # Measure End-to-End Generation
        t0 = time.time()
        try:
            res = await answer_sync(query, "eval_user", f"eval_{t_id}")
            latency = round(time.time() - t0, 2)
            res_text = res.get("answer", "")
            sources = res.get("sources", [])
        except Exception as e:
            latency = round(time.time() - t0, 2)
            res_text = f"ERROR: {e}"
            sources = []
        latencies.append(latency)

        score = score_item(res_text, retrieved_docs, gt)
        status_symbol = "✅ PASS" if score["passed"] else "❌ FAIL"

        print(f"       Status: {status_symbol} | Accuracy: {score['composite_accuracy']}% | Hit@k: {score['retrieval_hit_rate']}% | Lat: {latency}s (Ret: {t_ret}s)")
        if score["missing_facts"] and not gt.get("should_abstain"):
            print(f"       ⚠️ Missing Ground-Truth: {score['missing_facts']}")
        if score["hallucinations"]:
            print(f"       🚨 Hallucinated/Prohibited: {score['hallucinations']}")

        entry = {
            "id": t_id,
            "category": cat,
            "query": query,
            "latency": latency,
            "retrieval_latency": t_ret,
            "num_sources": len(sources),
            "score": score,
            "response_preview": res_text[:200].replace("\n", " ")
        }
        results.append(entry)

        # Rate-limit buffer between evaluation requests
        await asyncio.sleep(0.35)

        # Aggregate Category Stats
        if cat not in category_metrics:
            category_metrics[cat] = {
                "total": 0, "passed": 0, "accuracies": [],
                "retrieval_hits": [], "latencies": []
            }
        category_metrics[cat]["total"] += 1
        if score["passed"]:
            category_metrics[cat]["passed"] += 1
        category_metrics[cat]["accuracies"].append(score["composite_accuracy"])
        category_metrics[cat]["retrieval_hits"].append(score["retrieval_hit_rate"])
        category_metrics[cat]["latencies"].append(latency)

    # -------------------------------------------------------------
    # Latency Percentiles (p50, p90, p95, p99)
    # -------------------------------------------------------------
    p50_lat = np.percentile(latencies, 50) if latencies else 0.0
    p90_lat = np.percentile(latencies, 90) if latencies else 0.0
    p95_lat = np.percentile(latencies, 95) if latencies else 0.0
    p99_lat = np.percentile(latencies, 99) if latencies else 0.0

    print("\n" + "=" * 90)
    print("📊 PER-CATEGORY FACTUAL ACCURACY & RETRIEVAL BREAKDOWN")
    print("=" * 90)
    print(f"{'Category':<26} | {'Passed':<7} | {'Pass Rate':<9} | {'Avg Accuracy':<12} | {'Hit@k':<8} | {'Avg Lat':<7}")
    print("-" * 90)

    total_passed = sum(c["passed"] for c in category_metrics.values())
    total_cases = len(test_cases)
    all_acc = [r["score"]["composite_accuracy"] for r in results]
    all_hits = [r["score"]["retrieval_hit_rate"] for r in results]

    for cat, stats in category_metrics.items():
        pass_rate = (stats["passed"] / stats["total"]) * 100
        avg_acc = sum(stats["accuracies"]) / len(stats["accuracies"])
        avg_hit = sum(stats["retrieval_hits"]) / len(stats["retrieval_hits"])
        avg_lat = sum(stats["latencies"]) / len(stats["latencies"])
        print(f"{cat:<26} | {stats['passed']}/{stats['total']:<5} | {pass_rate:>7.1f}% | {avg_acc:>10.1f}% | {avg_hit:>6.1f}% | {avg_lat:>5.2f}s")

    overall_pass_rate = (total_passed / total_cases) * 100 if total_cases else 0.0
    overall_accuracy = sum(all_acc) / len(all_acc) if all_acc else 0.0
    overall_hit_rate = sum(all_hits) / len(all_hits) if all_hits else 0.0

    print("-" * 90)
    print(f"{'OVERALL RAG EVALUATION':<26} | {total_passed}/{total_cases:<5} | {overall_pass_rate:>7.1f}% | {overall_accuracy:>10.1f}% | {overall_hit_rate:>6.1f}% | {p50_lat:>5.2f}s (p50)")
    print("=" * 90)
    print(f"⏱️  LATENCY PROFILE: p50={p50_lat:.2f}s | p90={p90_lat:.2f}s | p95={p95_lat:.2f}s | p99={p99_lat:.2f}s")
    print("=" * 90)

    # Save comprehensive report
    out_report = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "deep_rag_fact_accuracy_report.json")
    with open(out_report, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_test_cases": total_cases,
            "overall_pass_rate": round(overall_pass_rate, 2),
            "overall_accuracy": round(overall_accuracy, 2),
            "overall_retrieval_hit_rate": round(overall_hit_rate, 2),
            "latency_profile": {
                "p50": round(float(p50_lat), 2),
                "p90": round(float(p90_lat), 2),
                "p95": round(float(p95_lat), 2),
                "p99": round(float(p99_lat), 2),
            },
            "category_metrics": category_metrics,
            "detailed_results": results
        }, f, indent=2)

    print(f"\n💾 Benchmark report exported to: {out_report}\n")
    return overall_pass_rate

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GNDEC RAG Automated Eval Harness")
    parser.add_argument("--gold", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "gold_set.jsonl"))
    parser.add_argument("--max", type=int, default=None)
    args = parser.parse_args()

    pass_rate = asyncio.run(run_evaluation(args.gold, args.max))
    sys.exit(0 if pass_rate >= 80.0 else 1)
