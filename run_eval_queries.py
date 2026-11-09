# run_eval_queries.py
import asyncio
import json
import os
import sys

# Ensure backend can be imported
sys.path.insert(0, os.path.abspath("."))

from backend.agent import answer_sync

QUESTIONS = [
    {
        "id": "q1_principal",
        "category": "Administration / Leadership",
        "query": "Who is the Principal of Guru Nanak Dev Engineering College (GNDEC) Ludhiana?"
    },
    {
        "id": "q2_btech_fees",
        "category": "Fee Structure",
        "query": "What is the B.Tech fee structure at GNDEC Ludhiana?"
    },
    {
        "id": "q3_btech_courses",
        "category": "Academic Programs",
        "query": "What undergraduate B.Tech courses and branches are offered at GNDEC Ludhiana?"
    },
    {
        "id": "q4_hod_cse",
        "category": "Department Leadership",
        "query": "Who is the Head of Department (HOD) of Computer Science and Engineering at GNDEC?"
    },
    {
        "id": "q5_history",
        "category": "History & Establishment",
        "query": "When was Guru Nanak Dev Engineering College established and who laid its foundation stone?"
    },
    {
        "id": "q6_affiliation",
        "category": "Affiliation & Autonomy",
        "query": "Which university is GNDEC affiliated with, and what is its autonomous status?"
    },
    {
        "id": "q7_leet_admission",
        "category": "Admissions & Eligibility",
        "query": "What is the eligibility and admission process for LEET (Lateral Entry) B.Tech at GNDEC?"
    },
    {
        "id": "q8_hostel",
        "category": "Campus & Hostels",
        "query": "What are the hostel fee details and accommodation facilities at GNDEC?"
    }
]

async def run_all():
    results = []
    print(f"Running {len(QUESTIONS)} evaluation queries through RAG pipeline...")

    for item in QUESTIONS:
        qid = item["id"]
        q = item["query"]
        cat = item["category"]
        print(f"\n--- [{qid}] {q} ---")
        try:
            res = await answer_sync(q, "eval_user", f"eval_sess_{qid}")
            answer = res.get("answer", "")
            sources = res.get("sources", [])
            print(f"RAG Response ({len(answer)} chars, {len(sources)} sources):\n{answer[:200]}...")
            results.append({
                "id": qid,
                "category": cat,
                "query": q,
                "rag_answer": answer,
                "sources_count": len(sources),
                "sources": [
                    {
                        "source_file": s.get("source_file", ""),
                        "section": s.get("section", ""),
                        "question": s.get("question", "")[:100]
                    }
                    for s in sources[:5]
                ]
            })
        except Exception as e:
            print(f"Error executing {qid}: {e}")
            results.append({
                "id": qid,
                "category": cat,
                "query": q,
                "rag_answer": f"ERROR: {e}",
                "sources_count": 0,
                "sources": []
            })

    with open("eval_results_rag.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("\n✅ Saved all RAG responses to eval_results_rag.json")

if __name__ == "__main__":
    asyncio.run(run_all())
