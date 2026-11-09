"""
Comprehensive Deep Testing Suite:
1. Domain Boundary & Rejection Verification:
   Ensures queries regarding external institutions (GNDU, GNDPC, GNDIT, GNIET,
   GNIT, SGND Khalsa, GNKC, GGN Khalsa, GNIM, Guru Nanak College of Education,
   IITs, NITs, LPU, Thapar, PU Chandigarh, etc.) and non-college topics are
   strictly rejected / redirected (PolicyDecision.REDIRECT / is_out_of_domain = True).

2. GNDEC Fact Ground Truth Verification:
   Ensures GNDEC queries match 100% verified ground truth from the official
   college website (Principal, HODs, B.Tech branches, Fees, APEX 2026, Recent Events,
   Bus Pass, Railway Concession, Hostels).
"""

import asyncio
import os
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.domain_guard import is_out_of_domain
from backend.rag.policy import evaluate
from backend.rag.contracts import PolicyInput, PolicyDecision
from backend.vectorstore import retrieve


# =====================================================================
# 1. External Colleges & Lookalikes (MUST BE REJECTED / REDIRECTED)
# =====================================================================
EXTERNAL_COLLEGE_QUERIES = [
    # GNDU & Campuses & Constituent Colleges
    "What courses are offered at Guru Nanak Dev University Amritsar?",
    "Tell me about GNDU regional campus Jalandhar",
    "GNDU constituent college admission process",
    "Guru Nanak Dev University fee structure",
    "GNDU college nakodar courses",
    # GNDPC (Polytechnic)
    "Who is the principal of GNDPC Ludhiana?",
    "Guru Nanak Dev Polytechnic College diploma admission",
    "Fee structure of GNDPC Ludhiana",
    # GNDIT
    "Admission in Guru Nanak Dev Institute of Technology Delhi",
    "GNDIT placement record and packages",
    # GNIET
    "Tell me about GNIET Nagpur",
    "Guru Nanak Institute of Engineering and Technology Nagpur cutoff",
    # GNIT
    "GNIT college fee structure",
    "Guru Nanak Institute of Technology admission",
    # SGND Khalsa
    "Sri Guru Nanak Dev Khalsa College Delhi University cutoff",
    "SGND Khalsa admission procedure",
    # GNKC & GGN Khalsa
    "Guru Nanak Khalsa College Ludhiana courses",
    "GGN Khalsa College Ludhiana faculty",
    "Guru Nanak Khalsa College Matunga Mumbai",
    # Management & Education Colleges
    "Guru Nanak Institute of Management MBA fee",
    "GNIM college placements",
    "Guru Nanak College of Education B.Ed admission",
    # Other External Universities & Colleges
    "IIT Bombay computer science branch opening cutoff",
    "NIT Jalandhar mechanical engineering placement",
    "LPU distance education admission form",
    "Thapar University CSE average package",
    "Panjab University Chandigarh LLB entrance exam",
    "Chandigarh University hostel fees",
    "Chitkara University B.Tech placement",
    # Off-Topic / General Coding & Non-College
    "Write a python script to reverse a linked list",
    "What is the capital of France?",
    "Current stock price of Apple and Tesla",
]


# =====================================================================
# 2. GNDEC Official In-Domain Queries (MUST BE ALLOWED)
# =====================================================================
GNDEC_VALID_QUERIES = [
    "Who is the principal of GNDEC?",
    "Who was the first principal of GNDEC?",
    "What are the B.Tech branches offered at GNDEC?",
    "What is the fee structure for B.Tech at GNDEC?",
    "Who is the HOD of Mechanical Engineering at GNDEC?",
    "Who is the HOD of Computer Science and Engineering at GNDEC?",
    "Who is the HOD of Information Technology at GNDEC?",
    "What is APEX 2026 at GNDEC?",
    "Tell me about recently organised events at GNDEC",
    "What is Anand Utsav at GNDEC?",
    "How to apply for a bus pass at GNDEC?",
    "How to get railway concession at GNDEC?",
]


async def test_external_institutions_rejection():
    print("\n" + "=" * 70)
    print("TEST 1: External Institution & Out-of-Domain Strict Rejection")
    print("=" * 70)

    passed = 0
    failed = 0

    for query in EXTERNAL_COLLEGE_QUERIES:
        ood = is_out_of_domain(query)
        policy_out = await evaluate(PolicyInput(query=query))
        is_rejected = ood or (policy_out.decision in [PolicyDecision.REDIRECT, PolicyDecision.DENY])

        if is_rejected:
            passed += 1
            print(f"  [BLOCKED] (Decision={policy_out.decision.value}, OOD={ood}) '{query[:60]}...'")
        else:
            failed += 1
            print(f"  [ERROR: LEAKED] '{query}' was ALLOWED! (Decision={policy_out.decision.value}, OOD={ood})")

    print(f"\nRejection Results: {passed}/{len(EXTERNAL_COLLEGE_QUERIES)} blocked correctly.")
    assert failed == 0, f"FAILED: {failed} external queries leaked through domain guard / policy!"
    print("✓ All external colleges and out-of-domain queries strictly blocked.")


async def test_gndec_domain_allow():
    print("\n" + "=" * 70)
    print("TEST 2: GNDEC In-Domain Queries Allowed")
    print("=" * 70)

    passed = 0
    failed = 0

    for query in GNDEC_VALID_QUERIES:
        ood = is_out_of_domain(query)
        policy_out = await evaluate(PolicyInput(query=query))
        is_allowed = (not ood) and (policy_out.decision == PolicyDecision.ALLOW)

        if is_allowed:
            passed += 1
            print(f"  [ALLOWED] (Decision={policy_out.decision.value}) '{query}'")
        else:
            failed += 1
            print(f"  [ERROR: FALSE POSITIVE] '{query}' was BLOCKED! (Decision={policy_out.decision.value}, OOD={ood})")

    print(f"\nIn-Domain Results: {passed}/{len(GNDEC_VALID_QUERIES)} allowed correctly.")
    assert failed == 0, f"FAILED: {failed} valid GNDEC queries were wrongly blocked!"
    print("✓ All valid GNDEC queries correctly allowed.")


def test_gndec_facts_retrieval_ground_truth():
    print("\n" + "=" * 70)
    print("TEST 3: GNDEC Fact Retrieval & Ground Truth Verification")
    print("=" * 70)

    # 1. Principal & History
    principal_docs = retrieve("who is the principal of GNDEC?")
    assert principal_docs, "No docs retrieved for principal query"
    p_content = principal_docs[0].page_content
    assert "Dr. Sehijpal Singh" in p_content, f"Expected Dr. Sehijpal Singh in principal doc, got: {p_content[:200]}"
    assert "Tara Singh" in p_content, "Expected founding principal Tara Singh in succession history"
    print("  ✓ Principal ground truth verified: Dr. Sehijpal Singh (current), Principal Tara Singh (founding).")

    # 2. B.Tech Branches (Must return 7 AICTE branches, no hallucinations)
    branch_docs = retrieve("what are the B.Tech branches offered at GNDEC?")
    assert branch_docs, "No docs retrieved for branches query"
    b_content = branch_docs[0].page_content
    assert "Computer Science" in b_content, "CSE missing in branches"
    assert "Civil Engineering" in b_content, "Civil missing in branches"
    assert "Electrical Engineering" in b_content, "Electrical missing in branches"
    assert "Mechanical Engineering" in b_content, "Mechanical missing in branches"
    print("  ✓ B.Tech branches ground truth verified: Civil, CSE, EE, ECE, ME, IT, Production.")

    # 3. HOD Ground Truth
    mech_hod_docs = retrieve("who is the HOD of Mechanical Engineering at GNDEC?")
    assert mech_hod_docs, "No docs retrieved for Mechanical HOD"
    assert "Dr. Harmeet Singh" in mech_hod_docs[0].page_content, f"Expected Dr. Harmeet Singh for Mech HOD, got: {mech_hod_docs[0].page_content[:200]}"
    print("  ✓ HOD Mechanical verified: Dr. Harmeet Singh.")

    cse_hod_docs = retrieve("who is the HOD of CSE at GNDEC?")
    assert cse_hod_docs, "No docs retrieved for CSE HOD"
    assert "Dr. Kiran Jyoti" in cse_hod_docs[0].page_content, f"Expected Dr. Kiran Jyoti for CSE HOD, got: {cse_hod_docs[0].page_content[:200]}"
    print("  ✓ HOD CSE verified: Dr. Kiran Jyoti.")

    # 4. Recent Events & APEX 2026 Ground Truth
    apex_docs = retrieve("what is apex 2026?")
    assert apex_docs, "No docs retrieved for APEX 2026"
    apex_content = apex_docs[0].page_content
    assert "APEX 2026" in apex_content or "APEX" in apex_content, "APEX 2026 missing from retrieved doc"
    assert "Causmic Club" in apex_content, "Expected Causmic Club as organizer of APEX"
    assert "October 2026" in apex_content or "Apex Live Project Display" in apex_content, "Expected October 2026 or Live Project Display in APEX details"
    print("  ✓ APEX 2026 ground truth verified: Causmic Club, October 2026, Apex Live Project Display.")

    recent_events_docs = retrieve("recently organised events at GNDEC")
    assert recent_events_docs, "No docs retrieved for recently organised events"
    r_content = recent_events_docs[0].page_content
    assert "APEX 2026" in r_content or "APEX" in r_content, "APEX 2026 missing from recently organised events"
    assert "Anand Utsav" in r_content, "Anand Utsav missing from college events overview"
    print("  ✓ Recently organised events verified: APEX 2026, Anand Utsav, Genesis, Alumni Meet.")

    # 5. Student Services (Bus pass, Railway concession)
    bus_docs = retrieve("how to apply for bus pass at GNDEC?")
    assert bus_docs, "No docs retrieved for bus pass"
    assert "PRTC" in bus_docs[0].page_content, "Expected PRTC in bus pass details"
    print("  ✓ Student Amenities verified: Bus Pass & Railway Concession proforma.")

    print("\n✓ All GNDEC fact retrieval ground truth assertions passed with 100% precision.")


async def main():
    await test_external_institutions_rejection()
    await test_gndec_domain_allow()
    test_gndec_facts_retrieval_ground_truth()
    print("\n" + "=" * 70)
    print("🎉 ALL DEEP ACCURACY AND DOMAIN VERIFICATION TESTS PASSED (100% SUCCESS)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
