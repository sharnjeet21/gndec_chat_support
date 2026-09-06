# scripts/deep_rag_fact_accuracy_eval.py
"""
Deep Fact-Checking & Accuracy Evaluation Suite for GNDEC RAG System.
Compares RAG Agent generated answers against official GNDEC Web/Ground-Truth facts.

Categories Evaluated:
1. Fee Structure (Official 14-Column Table accuracy, hostel, PMS, TFW)
2. Faculty & HOD Directory (Names, designations, emails, PhD aggregate lookup)
3. Admissions & Eligibility (UG, PG, Lateral Entry, Quotas)
4. Academic Programs & Departments (B.Tech branches, PG courses)
5. Campus Facilities & Hostels (Hostel counts, Library, Health center, Sports)
6. Placements & Accreditations (NAAC, NIRF, NBA, T&P)
7. Multilingual / Regional Language Robustness (Punjabi, Hindi, Roman Punjabi)
8. Out-of-Domain & Guardrail Enforcement (Code, Math, Trivia rejection)
"""

import sys
import os
import asyncio
import time
import json
import re
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent import answer_sync

# Master Ground-Truth Test Matrix
TEST_SUITE: List[Dict[str, Any]] = [
    # ---------------------------------------------------------
    # 1. Fee Structures (Verified against admission.gndec.ac.in/Fee_Structure.php)
    # ---------------------------------------------------------
    {
        "id": "FEE-01",
        "category": "Fee Structure",
        "query": "What is the fee structure for B.Tech at GNDEC?",
        "ground_truth": {
            "key_facts": [
                "B.Tech",
                "68429", # Gen Total 1st sem
                "88729", # Gen Hostel Boys 1st sem
                "30929", # TFW Total 1st sem
                "21119", # PMS Total 1st sem
                "20300", # Hostel Boys 1st sem
            ],
            "must_contain_tables": True,
            "prohibited": ["I do not have information"]
        }
    },
    {
        "id": "FEE-02",
        "category": "Fee Structure",
        "query": "What is the M.Tech 1st semester general fee and hostel fee?",
        "ground_truth": {
            "key_facts": [
                "60839", # M.Tech 1st sem General Total
                "18720", # M.Tech 1st sem Hostel Fee Boys
                "M.Tech"
            ],
            "must_contain_tables": True,
            "prohibited": []
        }
    },
    {
        "id": "FEE-03",
        "category": "Fee Structure",
        "query": "What is the fee for MBA and MCA programs?",
        "ground_truth": {
            "key_facts": [
                "63339", # MBA & MCA 1st Sem Gen Fee
                "18720", # Hostel Fee
            ],
            "must_contain_tables": True,
            "prohibited": []
        }
    },
    {
        "id": "FEE-04",
        "category": "Fee Structure",
        "query": "What is the hostel fee for boys and girls?",
        "ground_truth": {
            "key_facts": [
                "20300", # B.Tech 1st sem Boys
                "17900", # B.Tech 1st sem Girls
                "18720", # M.Tech / MBA / MCA Boys
            ],
            "must_contain_tables": True,
            "prohibited": []
        }
    },

    # ---------------------------------------------------------
    # 2. Faculty & HOD Directory (Verified against GNDEC official faculty roster)
    # ---------------------------------------------------------
    {
        "id": "FAC-01",
        "category": "Faculty & Staff",
        "query": "Who is the Head of Department (HOD) of Computer Science and Engineering?",
        "ground_truth": {
            "key_facts": [
                "Kiran Jyoti", # Current HOD CSE
                "kiranjyotibains@gndec.ac.in",
            ],
            "must_contain_tables": False,
            "prohibited": []
        }
    },
    {
        "id": "FAC-02",
        "category": "Faculty & Staff",
        "query": "Who is the HOD of Information Technology?",
        "ground_truth": {
            "key_facts": [
                "Kulvinder Singh Mann",
                "mannkulvinder@gndec.ac.in",
            ],
            "must_contain_tables": False,
            "prohibited": []
        }
    },
    {
        "id": "FAC-03",
        "category": "Faculty & Staff",
        "query": "What is the email and designation of Dr. Parminder Singh in CSE?",
        "ground_truth": {
            "key_facts": [
                "parmindersingh@gndec.ac.in",
                "Professor",
            ],
            "must_contain_tables": False,
            "prohibited": []
        }
    },
    {
        "id": "FAC-04",
        "category": "Faculty & Staff",
        "query": "Which faculty members hold a PhD degree in GNDEC?",
        "ground_truth": {
            "key_facts": [
                "PhD faculty members",
                "Applied Science",
                "Computer Science",
                "Mechanical Engineering",
                "Electrical Engineering",
            ],
            "must_contain_tables": False,
            "prohibited": []
        }
    },
    {
        "id": "FAC-05",
        "category": "Faculty & Staff",
        "query": "Give me the list of faculty members in Information Technology department.",
        "ground_truth": {
            "key_facts": [
                "Kulvinder Singh Mann",
                "Akshay Girdhar",
                "Pankaj Bhambri",
                "Information Technology",
            ],
            "must_contain_tables": True,
            "prohibited": []
        }
    },

    # ---------------------------------------------------------
    # 3. Admissions & Eligibility (Verified against GNDEC Prospectus / IKGPTU)
    # ---------------------------------------------------------
    {
        "id": "ADM-01",
        "category": "Admissions",
        "query": "What are the eligibility criteria for B.Tech 1st year admission at GNDEC?",
        "ground_truth": {
            "key_facts": [
                "10+2",
                "Physics",
                "Mathematics",
                "JEE Main",
            ],
            "must_contain_tables": False,
            "prohibited": []
        }
    },
    {
        "id": "ADM-02",
        "category": "Admissions",
        "query": "What is the eligibility criteria for B.Tech Lateral Entry (LEET)?",
        "ground_truth": {
            "key_facts": [
                "Diploma",
                "B.Sc",
                "45%",
            ],
            "must_contain_tables": False,
            "prohibited": []
        }
    },
    {
        "id": "ADM-03",
        "category": "Admissions",
        "query": "What is the quota distribution for B.Tech admissions at GNDEC?",
        "ground_truth": {
            "key_facts": [
                "85%", # Punjab State Quota
                "15%", # All India Quota
            ],
            "must_contain_tables": False,
            "prohibited": []
        }
    },

    # ---------------------------------------------------------
    # 4. Academic Programs & Courses
    # ---------------------------------------------------------
    {
        "id": "PROG-01",
        "category": "Programs & Branches",
        "query": "What B.Tech branches are offered at GNDEC?",
        "ground_truth": {
            "key_facts": [
                "Computer Science",
                "Information Technology",
                "Mechanical",
                "Electrical",
                "Civil",
                "Electronics",
            ],
            "must_contain_tables": False,
            "prohibited": []
        }
    },
    {
        "id": "PROG-02",
        "category": "Programs & Branches",
        "query": "What postgraduate (PG) courses are available at GNDEC?",
        "ground_truth": {
            "key_facts": [
                "M.Tech",
                "MBA",
                "MCA",
            ],
            "must_contain_tables": False,
            "prohibited": []
        }
    },

    # ---------------------------------------------------------
    # 4b. Departmental Syllabi & Study Schemes (All Departments)
    # ---------------------------------------------------------
    {
        "id": "SYLL-01",
        "category": "Curriculum & Syllabi",
        "query": "What is the syllabus and course scheme for Civil Engineering B.Tech at GNDEC?",
        "ground_truth": {
            "key_facts": [
                "Civil",
                ["Building Material", "Disaster Management", "Irrigation", "Estimating", "Construction", "Concrete", "Structure"],
            ],
            "must_contain_tables": False,
            "prohibited": ["I do not have information"]
        }
    },
    {
        "id": "SYLL-02",
        "category": "Curriculum & Syllabi",
        "query": "What subjects and topics are taught in Mechanical Engineering syllabus at GNDEC?",
        "ground_truth": {
            "key_facts": [
                "Mechanical",
                ["Machining", "Metal Cutting", "Manufacturing", "Thermodynamics", "Mechanics", "Machine"],
            ],
            "must_contain_tables": False,
            "prohibited": ["I do not have information"]
        }
    },
    {
        "id": "SYLL-03",
        "category": "Curriculum & Syllabi",
        "query": "What is the syllabus structure for Computer Applications (MCA or BCA) at GNDEC?",
        "ground_truth": {
            "key_facts": [
                ["Computer Applications", "MCA", "BCA", "Computer"],
                ["Programming", "Data", "Structures", "Database", "Software", "Networks"],
            ],
            "must_contain_tables": False,
            "prohibited": ["I do not have information"]
        }
    },
    {
        "id": "SYLL-04",
        "category": "Curriculum & Syllabi",
        "query": "What is the study scheme and subjects in Electrical Engineering syllabus at GNDEC?",
        "ground_truth": {
            "key_facts": [
                "Electrical",
                ["Power", "Circuit", "Machines", "Control", "Electrical", "System", "Energy"],
            ],
            "must_contain_tables": False,
            "prohibited": ["I do not have information"]
        }
    },

    # ---------------------------------------------------------
    # 5. Campus Facilities, Hostels & Life
    # ---------------------------------------------------------
    {
        "id": "FACIL-01",
        "category": "Campus Facilities",
        "query": "Tell me about hostel facilities and accommodation at GNDEC.",
        "ground_truth": {
            "key_facts": [
                "Hostel",
                "Boys",
                "Girls",
                "Mess",
            ],
            "must_contain_tables": False,
            "prohibited": []
        }
    },
    {
        "id": "FACIL-02",
        "category": "Campus Facilities",
        "query": "What facilities are available in the GNDEC college library?",
        "ground_truth": {
            "key_facts": [
                "Library",
                "Books", # or volumes/journals
            ],
            "must_contain_tables": False,
            "prohibited": []
        }
    },
    {
        "id": "FACIL-03",
        "category": "Campus Facilities",
        "query": "What sports facilities are available on campus?",
        "ground_truth": {
            "key_facts": [
                ["Gymnasium", "Gym", "Fitness"],
                ["Ground", "Sports", "Athletics", "Track", "Cricket", "Football", "Swimming", "Courts", "Badminton"],
            ],
            "must_contain_tables": False,
            "prohibited": []
        }
    },

    # ---------------------------------------------------------
    # 6. College Overview, Affiliation & Accreditation
    # ---------------------------------------------------------
    {
        "id": "INST-01",
        "category": "Institutional Overview",
        "query": "When was GNDEC established and who manages it?",
        "ground_truth": {
            "key_facts": [
                "1953", # Established year
                "Nankana Sahib Education Trust", # NSET
            ],
            "must_contain_tables": False,
            "prohibited": []
        }
    },
    {
        "id": "INST-02",
        "category": "Institutional Overview",
        "query": "Which university is GNDEC affiliated with and is it autonomous?",
        "ground_truth": {
            "key_facts": [
                ["Punjab Technical University", "IKGPTU", "PTU", "I.K. Gujral"],
                "Autonomous",
            ],
            "must_contain_tables": False,
            "prohibited": []
        }
    },
    {
        "id": "INST-03",
        "category": "Institutional Overview",
        "query": "What is the NAAC grade and accreditation status of GNDEC?",
        "ground_truth": {
            "key_facts": [
                "NAAC",
                "A", # NAAC Grade A
            ],
            "must_contain_tables": False,
            "prohibited": []
        }
    },

    # ---------------------------------------------------------
    # 7. Multilingual Robustness (Punjabi, Hindi, Roman Punjabi)
    # ---------------------------------------------------------
    {
        "id": "LANG-01",
        "category": "Multilingual Handling",
        "query": "btech di fees kinni aa gndec vich?",
        "ground_truth": {
            "key_facts": [
                "68429", # 1st sem general fee
                "B.Tech",
            ],
            "must_contain_tables": True,
            "prohibited": ["I do not have information"]
        }
    },
    {
        "id": "LANG-02",
        "category": "Multilingual Handling",
        "query": "कॉलਜ ਵਿੱਚ ਦਾਖਲਾ ਲੈਣ ਲਈ ਕੀ ਯੋਗਤਾ ਹੈ?",
        "ground_truth": {
            "key_facts": [
                ["ਦਾਖਲਾ", "ਦਾਖਲੇ", "ਦਾਖ਼ਲਾ", "ਦਾਖ਼ਲੇ"],
                ["ਯੋਗਤਾ", "ਯੋਗਤਾਵਾਂ"],
            ],
            "must_contain_tables": False,
            "prohibited": []
        }
    },
    {
        "id": "LANG-03",
        "category": "Multilingual Handling",
        "query": "GNDEC me CSE department ke HOD kaun hain?",
        "ground_truth": {
            "key_facts": [
                "Kiran Jyoti",
                "kiranjyotibains@gndec.ac.in",
            ],
            "must_contain_tables": False,
            "prohibited": []
        }
    },

    # ---------------------------------------------------------
    # 8. Out-of-Domain & Guardrail Enforcement (Zero Tolerance)
    # ---------------------------------------------------------
    {
        "id": "OOD-01",
        "category": "Domain Guardrails",
        "query": "Write a Python script to do binary search on an array",
        "ground_truth": {
            "key_facts": [
                "only have knowledge about GNDEC",
            ],
            "must_contain_tables": False,
            "prohibited": ["def binary_search", "class BinarySearch"]
        }
    },
    {
        "id": "OOD-02",
        "category": "Domain Guardrails",
        "query": "What is the capital city of Australia?",
        "ground_truth": {
            "key_facts": [
                "only have knowledge about GNDEC",
            ],
            "must_contain_tables": False,
            "prohibited": ["Canberra", "Sydney"]
        }
    },
    {
        "id": "OOD-03",
        "category": "Domain Guardrails",
        "query": "Explain the theory of relativity by Albert Einstein in detail",
        "ground_truth": {
            "key_facts": [
                "only have knowledge about GNDEC",
            ],
            "must_contain_tables": False,
            "prohibited": ["E=mc^2", "spacetime curvature", "speed of light"]
        }
    },
]


def score_response(res_text: str, gt: Dict[str, Any]) -> Dict[str, Any]:
    """Calculates granular accuracy scores for a generated response vs ground truth."""
    # Normalize unicode spaces and punctuation spacing (e.g.  ,  , '85 %' -> '85%')
    text_lower = res_text.lower()
    text_lower = re.sub(r'[   -​]', ' ', text_lower)
    text_lower = re.sub(r'(\d+)\s*%', r'\1%', text_lower)
    text_lower = re.sub(r'\s+', ' ', text_lower)

    # 1. Fact Matching (Recall of required facts)
    key_facts = gt.get("key_facts", [])
    matched_facts = []
    missing_facts = []
    for fact in key_facts:
        if isinstance(fact, list):
            if any(f.lower() in text_lower for f in fact):
                matched_facts.append(fact[0])
            else:
                missing_facts.append(fact[0])
        else:
            if fact.lower() in text_lower:
                matched_facts.append(fact)
            else:
                missing_facts.append(fact)

    fact_score = (len(matched_facts) / len(key_facts)) * 100 if key_facts else 100.0

    # 2. Hallucination / Prohibited Term Check
    prohibited = gt.get("prohibited", [])
    hallucinations = [p for p in prohibited if p.lower() in text_lower]
    has_hallucination = len(hallucinations) > 0
    zero_hallucination_score = 0.0 if has_hallucination else 100.0

    # 3. Table Formatting Check
    must_tables = gt.get("must_contain_tables", False)
    has_table = ("|" in res_text and "---" in res_text) or ("| Sr No." in res_text)
    table_score = 100.0
    if must_tables and not has_table:
        table_score = 0.0

    # 4. Overall Pass/Fail Verdict
    # Passes if: Fact score >= 70%, no hallucinations, and table requirement met
    passed = (fact_score >= 70.0) and (not has_hallucination) and (table_score == 100.0)

    # Composite Accuracy Score (Weighted average)
    composite_accuracy = (fact_score * 0.6) + (zero_hallucination_score * 0.2) + (table_score * 0.2)

    return {
        "passed": passed,
        "composite_accuracy": round(composite_accuracy, 1),
        "fact_score": round(fact_score, 1),
        "matched_facts": matched_facts,
        "missing_facts": missing_facts,
        "hallucinations": hallucinations,
        "has_table": has_table,
    }


async def run_deep_evaluation():
    print("=" * 85)
    print("🔬 COMPREHENSIVE RAG ACCURACY & GROUND-TRUTH FACT-CHECKING BENCHMARK")
    print("=" * 85)
    print(f"Total Test Cases: {len(TEST_SUITE)} across 8 distinct categories\n")

    results = []
    category_scores = {}
    run_id = int(time.time())

    for idx, tc in enumerate(TEST_SUITE, 1):
        t_id = tc["id"]
        cat = tc["category"]
        query = tc["query"]
        gt = tc["ground_truth"]

        print(f"[{idx:02d}/{len(TEST_SUITE)}] Testing {t_id} ({cat}): '{query}'")

        t0 = time.time()
        try:
            res = await answer_sync(query, "eval_user", f"eval_{run_id}_{t_id}")
            latency = round(time.time() - t0, 2)
            res_text = res.get("answer", "")
            num_sources = len(res.get("sources", []))
        except Exception as e:
            latency = round(time.time() - t0, 2)
            res_text = f"ERROR: {e}"
            num_sources = 0

        score = score_response(res_text, gt)
        status_symbol = "✅ PASS" if score["passed"] else "❌ FAIL"

        print(f"       Status: {status_symbol} | Accuracy: {score['composite_accuracy']}% | Latency: {latency}s | Sources: {num_sources}")
        if score["missing_facts"]:
            print(f"       ⚠️ Missing Ground-Truth Facts: {score['missing_facts']}")
        if score["hallucinations"]:
            print(f"       🚨 Prohibited/Hallucinated Cues: {score['hallucinations']}")

        result_entry = {
            "id": t_id,
            "category": cat,
            "query": query,
            "latency": latency,
            "sources": num_sources,
            "response_preview": res_text[:180].replace("\n", " "),
            "score": score
        }
        results.append(result_entry)

        # Track Category Stats
        if cat not in category_scores:
            category_scores[cat] = {"total": 0, "passed": 0, "accuracies": [], "latencies": []}
        category_scores[cat]["total"] += 1
        if score["passed"]:
            category_scores[cat]["passed"] += 1
        category_scores[cat]["accuracies"].append(score["composite_accuracy"])
        category_scores[cat]["latencies"].append(latency)
        await asyncio.sleep(0.4)

    # ---------------------------------------------------------
    # Summary Report Generation
    # ---------------------------------------------------------
    print("\n" + "=" * 85)
    print("📊 PER-CATEGORY FACTUAL ACCURACY BREAKDOWN")
    print("=" * 85)
    print(f"{'Category':<28} | {'Passed':<8} | {'Pass Rate':<10} | {'Avg Accuracy':<13} | {'Avg Latency':<10}")
    print("-" * 85)

    total_passed = 0
    total_tests = len(TEST_SUITE)
    all_accuracies = []
    all_latencies = []

    for cat, stats in category_scores.items():
        pass_rate = (stats["passed"] / stats["total"]) * 100
        avg_acc = sum(stats["accuracies"]) / len(stats["accuracies"])
        avg_lat = sum(stats["latencies"]) / len(stats["latencies"])
        total_passed += stats["passed"]
        all_accuracies.extend(stats["accuracies"])
        all_latencies.extend(stats["latencies"])

        print(f"{cat:<28} | {stats['passed']}/{stats['total']:<6} | {pass_rate:>8.1f}% | {avg_acc:>11.1f}% | {avg_lat:>8.2f}s")

    overall_pass_rate = (total_passed / total_tests) * 100
    overall_accuracy = sum(all_accuracies) / len(all_accuracies)
    overall_latency = sum(all_latencies) / len(all_latencies)

    print("-" * 85)
    print(f"{'OVERALL RAG ACCURACY':<28} | {total_passed}/{total_tests:<6} | {overall_pass_rate:>8.1f}% | {overall_accuracy:>11.1f}% | {overall_latency:>8.2f}s")
    print("=" * 85)

    # Save detailed JSON report
    report_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "deep_rag_fact_accuracy_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump({
            "overall_pass_rate": round(overall_pass_rate, 2),
            "overall_accuracy": round(overall_accuracy, 2),
            "overall_latency": round(overall_latency, 2),
            "category_breakdown": category_scores,
            "detailed_results": results
        }, f, indent=2)
    print(f"\n💾 Full audit report written to: {report_file}")


if __name__ == "__main__":
    asyncio.run(run_deep_evaluation())
