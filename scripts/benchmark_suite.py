import asyncio
import time
import json
from backend.agent import answer_sync

TEST_QUERIES = [
    # 1. Fee Structures (Structured 14-column tables)
    {"q": "What is the fee structure for B.Tech?", "cat": "Fee", "expect": "B.Tech."},
    {"q": "hostel di fees kinni aa", "cat": "Fee (Punjabi)", "expect": "Hostel"},
    {"q": "MBA and MCA fees detail", "cat": "Fee", "expect": "MBA/MCA"},
    {"q": "M.Tech fee structure", "cat": "Fee", "expect": "M.Tech."},
    {"q": "Lateral entry fee table", "cat": "Fee", "expect": "Lateral Entry"},
    {"q": "fees", "cat": "Fee (General)", "expect": "B.Tech."},

    # 2. Faculty Directory
    {"q": "Who is Dr. Parminder Singh?", "cat": "Faculty", "expect": "parmindersingh@gndec.ac.in"},
    {"q": "Tell me about Dr. Akshay Girdhar", "cat": "Faculty", "expect": "Information Technology"},
    {"q": "HOD of Civil Engineering department contact", "cat": "Faculty", "expect": "Civil"},
    {"q": "Dr. Kiran Jyoti email", "cat": "Faculty", "expect": "kiranjyotibains@gndec.ac.in"},

    # 3. Admissions & Courses
    {"q": "What B.Tech branches are offered at GNDEC?", "cat": "Admissions", "expect": "Computer Science"},
    {"q": "What are the eligibility criteria for MBA admission?", "cat": "Admissions", "expect": "Bachelor’s Degree"},
    {"q": "Is GNDEC autonomous or affiliated to IKGPTU?", "cat": "College Info", "expect": "Autonomous"},

    # 4. Multilingual Queries
    {"q": "GNDEC ch admission kive hundi aa?", "cat": "Multilingual (Punjabi)", "expect": "GNDEC"},
    {"q": "College me hostel facilities kaisi hai?", "cat": "Multilingual (Hindi)", "expect": "hostel"},

    # 5. Out of Domain & Safety
    {"q": "Write a python script to sort an array", "cat": "OOD/Safety", "expect": "only have knowledge about GNDEC"},
    {"q": "Who is the Prime Minister of France?", "cat": "OOD/Safety", "expect": "only have knowledge about GNDEC"},
]

async def run_benchmark():
    print(f"============================================================")
    print(f"🚀 Running Comprehensive RAG Benchmark Suite ({len(TEST_QUERIES)} queries)")
    print(f"============================================================\n")

    results = []
    total_latency = 0.0

    for i, item in enumerate(TEST_QUERIES, 1):
        q = item["q"]
        cat = item["cat"]
        exp = item["expect"]
        session = f"bench_{i}"

        start = time.time()
        res = await answer_sync(q, "benchmark_user", session)
        latency = round(time.time() - start, 2)
        total_latency += latency

        ans = res.get("answer", "")
        passed = exp.lower() in ans.lower()

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"[{i:02d}/{len(TEST_QUERIES):02d}] {status} ({latency}s) | [{cat}] {q}")
        if not passed:
            print(f"    Expected: {exp!r}")
            print(f"    Got: {ans[:150]!r}...")

        results.append({
            "query": q,
            "category": cat,
            "latency": latency,
            "passed": passed,
            "sources": len(res.get("sources", []))
        })

    passed_count = sum(1 for r in results if r["passed"])
    avg_latency = round(total_latency / len(results), 2)
    acc = round((passed_count / len(results)) * 100, 1)

    print("\n" + "=" * 60)
    print("📊 BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"Total Tests    : {len(results)}")
    print(f"Passed         : {passed_count}")
    print(f"Failed         : {len(results) - passed_count}")
    print(f"Accuracy Rate  : {acc}%")
    print(f"Avg Latency    : {avg_latency}s")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
