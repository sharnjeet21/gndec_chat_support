"""
tests/test_benchmark_prompts.py
================================
Automated test benchmark for 55 comprehensive GNDEC RAG prompts.
Evaluates:
  - Accuracy and presence of expected ground truth facts
  - Grounding & source attribution
  - Speed / latency
  - Out-of-scope guardrail adherence
"""

import time
import json
import urllib.parse
import urllib.request
import os

API_URL = "http://localhost:8000/api/ask"
API_KEY = "naman@1234"

PROMPTS = [
    # ── Category 1: General College & Foundation (1-5) ──
    {
        "id": 1,
        "category": "General & Foundation",
        "prompt": "When was GNDEC established and under which trust?",
        "expected_terms": ["1956", "nankana sahib", "trust"],
    },
    {
        "id": 2,
        "category": "General & Foundation",
        "prompt": "Is GNDEC an autonomous college and which university is it affiliated to?",
        "expected_terms": ["autonomous", "ugc", "ptu", "ikg"],
    },
    {
        "id": 3,
        "category": "General & Foundation",
        "prompt": "Where is GNDEC located and how to reach the college?",
        "expected_terms": ["gill road", "ludhiana", "141006"],
    },
    {
        "id": 4,
        "category": "General & Foundation",
        "prompt": "What is the official contact email and phone number of GNDEC principal?",
        "expected_terms": ["principal@gndec.ac.in", "0161-5064501"],
    },
    {
        "id": 5,
        "category": "General & Foundation",
        "prompt": "What is the NAAC accreditation grade of GNDEC?",
        "expected_terms": ["naac", "a"],
    },

    # ── Category 2: Principals & Leadership (6-9) ──
    {
        "id": 6,
        "category": "Leadership",
        "prompt": "Who is the current principal of GNDEC?",
        "expected_terms": ["sehijpal", "singh"],
    },
    {
        "id": 7,
        "category": "Leadership",
        "prompt": "Who was the first principal of GNDEC?",
        "expected_terms": ["tara", "singh"],
    },
    {
        "id": 8,
        "category": "Leadership",
        "prompt": "Give me the list of all principals of GNDEC from foundation till current",
        "expected_terms": ["tara singh", "sehijpal singh", "m.s. saini"],
    },
    {
        "id": 9,
        "category": "Leadership",
        "prompt": "What are the qualifications of Dr. Sehijpal Singh?",
        "expected_terms": ["ph.d", "iit roorkee", "gndec"],
    },

    # ── Category 3: B.Tech Programs & Branches (10-14) ──
    {
        "id": 10,
        "category": "Programs & Branches",
        "prompt": "What B.Tech branches are offered at GNDEC?",
        "expected_terms": ["civil", "computer science", "electrical", "electronics", "information technology", "mechanical", "production"],
    },
    {
        "id": 11,
        "category": "Programs & Branches",
        "prompt": "Does GNDEC offer B.Tech in Biotechnology or Chemical Engineering?",
        "expected_terms": ["does not offer", "only 7", "civil", "computer science"],
        "negative_terms": ["yes, it offers biotechnology"],
    },
    {
        "id": 12,
        "category": "Programs & Branches",
        "prompt": "What is the duration and curriculum structure of B.Tech at GNDEC?",
        "expected_terms": ["4", "year", "credit", "cbcs", "semester"],
    },
    {
        "id": 13,
        "category": "Programs & Branches",
        "prompt": "What postgraduate PG degree courses are available at GNDEC?",
        "expected_terms": ["m.tech", "mba", "mca"],
    },
    {
        "id": 14,
        "category": "Programs & Branches",
        "prompt": "Tell me about BCA course at GNDEC",
        "expected_terms": ["bca", "computer applications", "3-year", "10+2"],
    },

    # ── Category 4: Admissions, Quotas & Eligibility (15-22) ──
    {
        "id": 15,
        "category": "Admissions",
        "prompt": "What is the complete admission process for B.Tech 1st year at GNDEC?",
        "expected_terms": ["jee main", "counseling", "ptu", "admission.gndec.ac.in"],
    },
    {
        "id": 16,
        "category": "Admissions",
        "prompt": "What is the Rural Quota at GNDEC and what percentage is reserved?",
        "expected_terms": ["70%", "rural", "5 years", "school"],
    },
    {
        "id": 17,
        "category": "Admissions",
        "prompt": "What are the eligibility criteria for claiming Rural Quota at GNDEC?",
        "expected_terms": ["rural", "certificate", "tehsildar", "sarpanch", "punjab"],
    },
    {
        "id": 18,
        "category": "Admissions",
        "prompt": "What entrance exam is required for B.Tech admission at GNDEC?",
        "expected_terms": ["jee main", "nta"],
    },
    {
        "id": 19,
        "category": "Admissions",
        "prompt": "How to get lateral entry LEET admission in 2nd year B.Tech at GNDEC?",
        "expected_terms": ["diploma", "leet", "3rd semester", "45%"],
    },
    {
        "id": 20,
        "category": "Admissions",
        "prompt": "What is the admission procedure for MBA at GNDEC?",
        "expected_terms": ["cmat", "bachelor", "50%"],
    },
    {
        "id": 21,
        "category": "Admissions",
        "prompt": "How to get admission in MCA at GNDEC?",
        "expected_terms": ["merit", "bca", "b.sc", "mathematics"],
    },
    {
        "id": 22,
        "category": "Admissions",
        "prompt": "What is Sikh Religion Exam SRE at GNDEC?",
        "expected_terms": ["sre", "sikh", "minority", "quota"],
    },

    # ── Category 5: Fee Structures (23-28) ──
    {
        "id": 23,
        "category": "Fee Structure",
        "prompt": "What is the B.Tech 1st semester fee structure for General category students at GNDEC?",
        "expected_terms": ["68429", "88729"],
    },
    {
        "id": 24,
        "category": "Fee Structure",
        "prompt": "What is the B.Tech fee for TFW Tuition Fee Waiver category in 1st semester?",
        "expected_terms": ["30929", "tfw"],
    },
    {
        "id": 25,
        "category": "Fee Structure",
        "prompt": "What is the Post Matric Scholarship PMS fee for B.Tech 1st sem at GNDEC?",
        "expected_terms": ["21119", "pms"],
    },
    {
        "id": 26,
        "category": "Fee Structure",
        "prompt": "What is the MBA and MCA 1st semester fee at GNDEC for General category?",
        "expected_terms": ["63339", "mba"],
    },
    {
        "id": 27,
        "category": "Fee Structure",
        "prompt": "What is the hostel fee for boys and girls in B.Tech 1st semester?",
        "expected_terms": ["20300", "17900"],
    },
    {
        "id": 28,
        "category": "Fee Structure",
        "prompt": "What are the hostel charges for B.Tech semester 2?",
        "expected_terms": ["15300", "12900"],
    },

    # ── Category 6: Department HoDs & Faculty (29-35) ──
    {
        "id": 29,
        "category": "Faculty",
        "prompt": "Who is the HoD of Information Technology department at GNDEC?",
        "expected_terms": ["mann", "it@gndec.ac.in"],
    },
    {
        "id": 30,
        "category": "Faculty",
        "prompt": "Who is Dr. Palwinder Kaur Bhangu at GNDEC?",
        "expected_terms": ["assistant professor", "information technology", "ph.d"],
    },
    {
        "id": 31,
        "category": "Faculty",
        "prompt": "Who is the HoD of Computer Science and Engineering CSE department?",
        "expected_terms": ["computer science", "head"],
    },
    {
        "id": 32,
        "category": "Faculty",
        "prompt": "Who is the HoD of Civil Engineering at GNDEC?",
        "expected_terms": ["civil", "head"],
    },
    {
        "id": 33,
        "category": "Faculty",
        "prompt": "Who is the HoD of Mechanical Engineering at GNDEC?",
        "expected_terms": ["mechanical", "head"],
    },
    {
        "id": 34,
        "category": "Faculty",
        "prompt": "How many faculty members have PhD degrees at GNDEC?",
        "expected_terms": ["phd", "faculty", "gndec"],
    },
    {
        "id": 35,
        "category": "Faculty",
        "prompt": "Who is Sharnjeet Singh at GNDEC?",
        "expected_terms": ["not have information", "charnjeet"],
    },

    # ── Category 7: Student Services & Forms (36-41) ──
    {
        "id": 36,
        "category": "Student Services",
        "prompt": "How to apply for a bus pass at GNDEC and where to get the form?",
        "expected_terms": ["prtc", "punjab roadways", "downloads", "student section"],
    },
    {
        "id": 37,
        "category": "Student Services",
        "prompt": "Where can students download the PRTC and Punjab Roadways bus pass forms?",
        "expected_terms": ["gndec.ac.in", "downloads"],
    },
    {
        "id": 38,
        "category": "Student Services",
        "prompt": "How to get a railway concession form at GNDEC?",
        "expected_terms": ["railway concession", "student section", "downloads"],
    },
    {
        "id": 39,
        "category": "Student Services",
        "prompt": "What hostel facilities are available for boys and girls at GNDEC?",
        "expected_terms": ["5", "boys", "girls", "mess", "wi-fi"],
    },
    {
        "id": 40,
        "category": "Student Services",
        "prompt": "How can students get a Bonafide or Character certificate at GNDEC?",
        "expected_terms": ["bonafide", "student section", "downloads"],
    },
    {
        "id": 41,
        "category": "Student Services",
        "prompt": "What is the procedure to reset college internet WiFi login password?",
        "expected_terms": ["internet", "password", "central computer center", "downloads"],
    },

    # ── Category 8: Examination & Academic Rules (42-46) ──
    {
        "id": 42,
        "category": "Academic Rules",
        "prompt": "What is the minimum attendance requirement to appear in exams at GNDEC?",
        "expected_terms": ["75%", "attendance", "end-semester"],
    },
    {
        "id": 43,
        "category": "Academic Rules",
        "prompt": "Can attendance shortage be condoned at GNDEC and up to how much?",
        "expected_terms": ["10%", "65%", "director"],
    },
    {
        "id": 44,
        "category": "Academic Rules",
        "prompt": "What is the internal and external examination weightage at GNDEC?",
        "expected_terms": ["60%", "40%", "mse", "ese"],
    },
    {
        "id": 45,
        "category": "Academic Rules",
        "prompt": "How many Mid-Semester Exams MSEs are conducted per semester?",
        "expected_terms": ["two", "mid-semester"],
    },
    {
        "id": 46,
        "category": "Academic Rules",
        "prompt": "What is the maximum period allowed to complete B.Tech at GNDEC?",
        "expected_terms": ["6 years", "lateral", "8"],
    },

    # ── Category 9: Placement & Training (47-50) ──
    {
        "id": 47,
        "category": "Training & Placement",
        "prompt": "Tell me about Training and Placement Cell TPO at GNDEC",
        "expected_terms": ["tpo", "placement", "training"],
    },
    {
        "id": 48,
        "category": "Training & Placement",
        "prompt": "Which companies visit GNDEC for campus placements?",
        "expected_terms": ["tcs", "infosys", "placement", "recruiters"],
    },
    {
        "id": 49,
        "category": "Training & Placement",
        "prompt": "What are the facilities at Central Computer Center CCC at GNDEC?",
        "expected_terms": ["computer center", "ccc", "internet", "lab"],
    },
    {
        "id": 50,
        "category": "Training & Placement",
        "prompt": "Which FDP is currently live or conducted at GNDEC?",
        "expected_terms": ["fdp", "design thinking", "atal", "generative ai"],
    },

    # ── Category 10: Guardrail / Out-of-Scope Negative Tests (51-55) ──
    {
        "id": 51,
        "category": "Guardrail Check",
        "prompt": "What is the fee structure of IIT Bombay for Computer Science?",
        "expected_terms": ["gndec", "only", "not provide"],
        "negative_terms": ["iit bombay fee is"],
    },
    {
        "id": 52,
        "category": "Guardrail Check",
        "prompt": "Who is the President of the United States?",
        "expected_terms": ["gndec", "assist", "only"],
        "negative_terms": ["joe biden", "donald trump"],
    },
    {
        "id": 53,
        "category": "Guardrail Check",
        "prompt": "How to get admission in Harvard University medical school?",
        "expected_terms": ["gndec", "only", "college"],
        "negative_terms": ["harvard admission requires"],
    },
    {
        "id": 54,
        "category": "Guardrail Check",
        "prompt": "Write a python script to sort a list of numbers",
        "expected_terms": ["gndec", "assistant", "only"],
    },
    {
        "id": 55,
        "category": "Guardrail Check",
        "prompt": "Tell me about Thapar University Patiala placements",
        "expected_terms": ["gndec", "only"],
    },
]


def _clean_str(text: str) -> str:
    import re
    # Collapse all whitespace and unicode non-breaking spaces, remove commas
    return re.sub(r"[\s\u202f\u00a0]+", " ", text).replace(",", "").lower().strip()


def test_prompt(item):
    p_id = item["id"]
    query = item["prompt"]
    encoded_q = urllib.parse.quote(query)
    url = f"{API_URL}?phone=eval_user&session_id=benchmark_sess_{p_id}&q={encoded_q}"

    req = urllib.request.Request(url, headers={"X-API-KEY": API_KEY})
    start_t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            elapsed = time.time() - start_t
            data = json.loads(resp.read().decode("utf-8"))
            ans = data.get("answer", "")
            sources = data.get("sources", [])
            status = data.get("verification_status", "unknown")

            norm_ans = _clean_str(ans)

            # Check expected terms
            missing_terms = [
                t for t in item.get("expected_terms", [])
                if _clean_str(t) not in norm_ans
            ]

            # Check negative terms (terms that must NOT be in answer)
            found_negative = [
                t for t in item.get("negative_terms", [])
                if _clean_str(t) in norm_ans
            ]

            passed = (len(missing_terms) == 0) and (len(found_negative) == 0)

            return {
                "id": p_id,
                "category": item["category"],
                "prompt": query,
                "passed": passed,
                "elapsed": round(elapsed, 2),
                "answer_snippet": ans[:150].replace("\n", " "),
                "missing_terms": missing_terms,
                "found_negative": found_negative,
                "sources_count": len(sources),
                "verification": status,
                "error": None,
            }
    except Exception as e:
        elapsed = time.time() - start_t
        return {
            "id": p_id,
            "category": item["category"],
            "prompt": query,
            "passed": False,
            "elapsed": round(elapsed, 2),
            "answer_snippet": "",
            "missing_terms": item.get("expected_terms", []),
            "found_negative": [],
            "sources_count": 0,
            "verification": "error",
            "error": str(e),
        }


def main():
    print(f"\n=======================================================")
    print(f"🚀 Running Comprehensive GNDEC Benchmark on {len(PROMPTS)} Prompts")
    print(f"=======================================================\n")

    results = []
    passed_cnt = 0

    for i, p in enumerate(PROMPTS, 1):
        res = test_prompt(p)
        results.append(res)
        if res["passed"]:
            passed_cnt += 1
            status_symbol = "✅ PASS"
        else:
            status_symbol = "❌ FAIL"

        print(f"[{i:02d}/{len(PROMPTS):02d}] {status_symbol} ({res['elapsed']}s) [{res['category']}] Q: {res['prompt'][:45]}...")
        if not res["passed"]:
            if res["missing_terms"]:
                print(f"       Missing: {res['missing_terms']}")
            if res["found_negative"]:
                print(f"       Forbidden found: {res['found_negative']}")
            if res["error"]:
                print(f"       Error: {res['error']}")
            print(f"       Ans: {res['answer_snippet']}")

        time.sleep(0.3)

    print("\n" + "="*55)
    print(f"📊 BENCHMARK SUMMARY: {passed_cnt}/{len(PROMPTS)} Passed ({passed_cnt*100.0/len(PROMPTS):.1f}%)")
    print("="*55)

    # Save detailed report
    report_file = "tests/benchmark_results.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump({"total": len(PROMPTS), "passed": passed_cnt, "results": results}, f, indent=2)
    print(f"💾 Full results saved to {report_file}\n")


if __name__ == "__main__":
    main()
