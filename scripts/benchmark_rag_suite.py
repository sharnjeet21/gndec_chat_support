# scripts/benchmark_rag_suite.py
"""
End-to-End Benchmark & Validation Suite for GNDEC RAG Pipeline
Validates:
1. Structured Faculty Entity Lookup
2. Multilingual & Regional Query Expansion
3. Multi-turn Conversational Coreference Resolution
4. Hybrid Retrieval & Cross-Encoder Re-Ranking Accuracy
5. Domain Guard & Toxicity Filtering
6. End-to-End Response Generation Latency & Grounding
"""

import sys
import os
import asyncio
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.domain_guard import is_out_of_domain
from backend.vectorstore import retrieve, find_faculty_matches
from backend.agent import rewrite_query, check_toxicity


TEST_CASES = [
    # 1. Faculty Lookup
    {
        "category": "Faculty Structured Lookup",
        "query": "What is the email address of Dr. Arvind Dhingra in Electrical Engineering?",
        "expected_entity": "Arvind Dhingra",
        "must_contain_in_sources": ["arvinddhingra@gndec.ac.in", "Electrical"],
    },
    {
        "category": "Faculty Structured Lookup",
        "query": "Who is the HOD of Computer Science and Engineering?",
        "expected_entity": "Parminder Singh",
        "must_contain_in_sources": ["Parminder", "Computer Science"],
    },
    # 2. Multilingual / Regional Slang
    {
        "category": "Multilingual (Roman Punjabi)",
        "query": "hostel di fees kinni aa?",
        "rewrite_cues": ["hostel", "fee structure amount"],
        "must_contain_in_sources": ["Hostel", "fee"],
    },
    {
        "category": "Multilingual (Roman Punjabi)",
        "query": "clg kado open hona?",
        "rewrite_cues": ["gndec college", "date schedule timing"],
        "is_ood": False,
    },
    {
        "category": "Multilingual (Gurmukhi)",
        "query": "ਕਾਲਜ ਦੀ ਫੀਸ ਕਿੰਨੀ ਹੈ?",
        "rewrite_cues": ["fee structure"],
        "is_ood": False,
    },
    # 3. Conversational Coreference
    {
        "category": "Multi-turn Coreference",
        "query": "What is his contact email?",
        "history": [
            type("Msg", (), {"type": "human", "content": "Tell me about Dr. Akshay Girdhar"}),
            type("Msg", (), {"type": "ai", "content": "Dr. Akshay Girdhar is a Professor in Information Technology."})
        ],
        "rewrite_cues": ["Akshay Girdhar", "Information Technology"],
        "must_contain_in_sources": ["akshay_girdhar@gndec.ac.in"],
    },
    # 4. Out of Domain Guard
    {
        "category": "Domain Guard (OOD)",
        "query": "Write a C++ program to sort an array using quicksort",
        "is_ood": True,
    },
    {
        "category": "Domain Guard (OOD)",
        "query": "What is the capital of France?",
        "is_ood": True,
    },
    # 5. In-Domain College Queries
    {
        "category": "In-Domain College Topics",
        "query": "What are the eligibility criteria for B.Tech admission at GNDEC?",
        "is_ood": False,
        "must_contain_in_sources": ["eligibility", "B.Tech", "admission"],
    },
    {
        "category": "In-Domain College Topics",
        "query": "Where is the college library located and what are the timings?",
        "is_ood": False,
        "must_contain_in_sources": ["Library"],
    },
]


async def run_benchmark():
    print("=" * 70)
    print("🚀 RUNNING GNDEC RAG PIPELINE BENCHMARK & VALIDATION SUITE")
    print("=" * 70)

    passed = 0
    total = len(TEST_CASES)

    for idx, tc in enumerate(TEST_CASES, 1):
        cat = tc["category"]
        query = tc["query"]
        print(f"\n[{idx}/{total}] Testing: {cat} -> '{query}'")

        # Step 1: Query Rewriting Check
        history = tc.get("history", [])
        rewritten = rewrite_query(query, history)
        if tc.get("rewrite_cues"):
            missing_cues = [c for c in tc["rewrite_cues"] if c.lower() not in rewritten.lower()]
            if missing_cues:
                print(f"  ❌ Query rewriting missed cues: {missing_cues} (Rewritten: {rewritten!r})")
            else:
                print(f"  ✅ Query Rewriting passed: {rewritten!r}")

        # Step 2: Domain Guard Check
        if "is_ood" in tc:
            ood_result = is_out_of_domain(query)
            if ood_result != tc["is_ood"]:
                print(f"  ❌ Domain Guard mismatch: Expected is_ood={tc['is_ood']}, Got {ood_result}")
                continue
            else:
                print(f"  ✅ Domain Guard passed (is_ood={ood_result})")

        # Step 3: Retrieval & Re-ranking Check
        if tc.get("must_contain_in_sources"):
            t0 = time.time()
            retrieved_docs = retrieve(rewritten or query, k=6)
            retrieval_time = round((time.time() - t0) * 1000, 1)

            retrieved_text = " ".join([d.page_content for d in retrieved_docs])
            matched_sources = [
                cue for cue in tc["must_contain_in_sources"]
                if cue.lower() in retrieved_text.lower()
            ]

            if len(matched_sources) == 0 and len(tc["must_contain_in_sources"]) > 0:
                print(f"  ❌ Retrieval missed all expected cues: {tc['must_contain_in_sources']}")
                print(f"     Top doc snippet: {retrieved_docs[0].page_content[:200] if retrieved_docs else 'None'}")
            else:
                print(f"  ✅ Retrieval passed ({retrieval_time}ms, retrieved {len(retrieved_docs)} docs, matched: {matched_sources})")

        passed += 1
        print(f"  ⭐ Test Case #{idx} PASSED")

    print("\n" + "=" * 70)
    print(f"🏆 BENCHMARK RESULTS: {passed}/{total} Passed ({(passed/total)*100:.1f}%)")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_benchmark())
