# scripts/generate_gold_set.py
"""
Generates the comprehensive, stratified Ground-Truth Gold Set for GNDEC RAG Evaluation.
Saves to data/gold_set.jsonl.
"""

import os
import json

GOLD_ITEMS = [
    # =========================================================================
    # 1. FEE STRUCTURE (Official 14-column tables & values)
    # =========================================================================
    {
        "id": "GOLD-FEE-001",
        "category": "Fee Structure",
        "query": "What is the complete fee structure for B.Tech at GNDEC?",
        "ground_truth": {
            "key_facts": ["68429", "88729", "30929", "21119", "20300", "58190", "59739"],
            "must_contain_tables": True,
            "prohibited": ["I do not have information"],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-FEE-002",
        "category": "Fee Structure",
        "query": "What is the 1st semester B.Tech General category fee without hostel?",
        "ground_truth": {
            "key_facts": ["68429", "B.Tech"],
            "must_contain_tables": True,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-FEE-003",
        "category": "Fee Structure",
        "query": "How much is the Tuition Fee Waiver (TFW) 1st semester fee for B.Tech?",
        "ground_truth": {
            "key_facts": ["30929", "TFW"],
            "must_contain_tables": True,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-FEE-004",
        "category": "Fee Structure",
        "query": "What is the Post Matric Scholarship (PMS) fee for B.Tech first semester?",
        "ground_truth": {
            "key_facts": ["21119", "PMS"],
            "must_contain_tables": True,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-FEE-005",
        "category": "Fee Structure",
        "query": "What is the M.Tech 1st semester general fee and hostel fee?",
        "ground_truth": {
            "key_facts": ["60839", "18720", "M.Tech"],
            "must_contain_tables": True,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-FEE-006",
        "category": "Fee Structure",
        "query": "Give me the full fee table for MBA and MCA programs.",
        "ground_truth": {
            "key_facts": ["63339", "18720", "MBA", "MCA"],
            "must_contain_tables": True,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-FEE-007",
        "category": "Fee Structure",
        "query": "What is the hostel fee for boys in 1st semester B.Tech vs M.Tech?",
        "ground_truth": {
            "key_facts": ["20300", "18720"],
            "must_contain_tables": True,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-FEE-008",
        "category": "Fee Structure",
        "query": "What is the girls hostel fee in 1st semester B.Tech?",
        "ground_truth": {
            "key_facts": ["17900"],
            "must_contain_tables": True,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-FEE-009",
        "category": "Fee Structure",
        "query": "What is the B.Voc and BBA/BCA fee structure?",
        "ground_truth": {
            "key_facts": ["BBA", "BCA", "41589"],
            "must_contain_tables": True,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-FEE-010",
        "category": "Fee Structure",
        "query": "What is the 2nd semester general fee for B.Tech?",
        "ground_truth": {
            "key_facts": ["58190"],
            "must_contain_tables": True,
            "prohibited": [],
            "should_abstain": False
        }
    },

    # =========================================================================
    # 2. FACULTY & HOD DIRECTORY
    # =========================================================================
    {
        "id": "GOLD-FAC-001",
        "category": "Faculty Directory",
        "query": "Who is the Head of Department (HOD) of Computer Science and Engineering?",
        "ground_truth": {
            "key_facts": ["Kiran Jyoti", "kiranjyotibains@gndec.ac.in"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-FAC-002",
        "category": "Faculty Directory",
        "query": "Who is the HOD of Information Technology department?",
        "ground_truth": {
            "key_facts": ["Kulvinder Singh Mann", "mannkulvinder@gndec.ac.in"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-FAC-003",
        "category": "Faculty Directory",
        "query": "Who is the Head of Mechanical Engineering department?",
        "ground_truth": {
            "key_facts": ["Harwinder Singh", "hs_gndec@gndec.ac.in"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-FAC-004",
        "category": "Faculty Directory",
        "query": "Who is the HOD of Electrical Engineering?",
        "ground_truth": {
            "key_facts": ["Kanwardeep Singh"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-FAC-005",
        "category": "Faculty Directory",
        "query": "Who is the HOD of Civil Engineering?",
        "ground_truth": {
            "key_facts": ["Prashant Garg"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-FAC-006",
        "category": "Faculty Directory",
        "query": "Who is the HOD of Electronics and Communication Engineering (ECE)?",
        "ground_truth": {
            "key_facts": ["Narwant Singh Grewal"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-FAC-007",
        "category": "Faculty Directory",
        "query": "Who is the Principal / Director of GNDEC Ludhiana?",
        "ground_truth": {
            "key_facts": ["Sehijpal Singh"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-FAC-008",
        "category": "Faculty Directory",
        "query": "Which faculty members hold a PhD degree in GNDEC?",
        "ground_truth": {
            "key_facts": ["104 faculty members", "Computer Science", "Mechanical", "Civil", "Electrical"],
            "must_contain_tables": True,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-FAC-009",
        "category": "Faculty Directory",
        "query": "List all faculty members in Information Technology department.",
        "ground_truth": {
            "key_facts": ["Kulvinder Singh Mann", "Akshay Girdhar", "Pankaj Bhambri", "Kamaljit Kaur"],
            "must_contain_tables": True,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-FAC-010",
        "category": "Faculty Directory",
        "query": "What is the designation and email of Dr. Parminder Singh in CSE?",
        "ground_truth": {
            "key_facts": ["parmindersingh@gndec.ac.in", "Professor", "Computer Science"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },

    # =========================================================================
    # 3. ADMISSIONS & ELIGIBILITY
    # =========================================================================
    {
        "id": "GOLD-ADM-001",
        "category": "Admissions & Eligibility",
        "query": "What is the eligibility criteria for B.Tech 1st year admission at GNDEC?",
        "ground_truth": {
            "key_facts": ["10+2", "Physics", "Mathematics", "JEE Main"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-ADM-002",
        "category": "Admissions & Eligibility",
        "query": "What are the eligibility requirements for B.Tech Lateral Entry (LEET)?",
        "ground_truth": {
            "key_facts": ["Diploma", "45%", "3 years"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-ADM-003",
        "category": "Admissions & Eligibility",
        "query": "What is the quota percentage for Punjab State vs Other States in B.Tech?",
        "ground_truth": {
            "key_facts": ["85%", "15%", "Punjab", "All India"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-ADM-004",
        "category": "Admissions & Eligibility",
        "query": "What is the eligibility for M.Tech admissions at GNDEC?",
        "ground_truth": {
            "key_facts": ["B.Tech", "B.E.", "50%", "GATE"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-ADM-005",
        "category": "Admissions & Eligibility",
        "query": "What is the eligibility criteria for MBA admission?",
        "ground_truth": {
            "key_facts": ["Bachelor", "Graduation", "50%", "CMAT"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-ADM-006",
        "category": "Admissions & Eligibility",
        "query": "What is the eligibility criteria for MCA admission at GNDEC?",
        "ground_truth": {
            "key_facts": ["BCA", "B.Sc", "Mathematics", "50%"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-ADM-007",
        "category": "Admissions & Eligibility",
        "query": "What documents are required during B.Tech admission counseling?",
        "ground_truth": {
            "key_facts": ["10th", "10+2", "JEE Main", "Certificate", "Domicile"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },

    # =========================================================================
    # 4. ACADEMIC PROGRAMS & DEPARTMENTS
    # =========================================================================
    {
        "id": "GOLD-PROG-001",
        "category": "Academic Programs",
        "query": "Which undergraduate B.Tech degree programs are offered at GNDEC?",
        "ground_truth": {
            "key_facts": ["Computer Science", "Information Technology", "Civil", "Mechanical", "Electrical", "Electronics"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-PROG-002",
        "category": "Academic Programs",
        "query": "What postgraduate (PG) courses can I study at GNDEC?",
        "ground_truth": {
            "key_facts": ["M.Tech", "MBA", "MCA", "M.Sc"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-PROG-003",
        "category": "Academic Programs",
        "query": "Does GNDEC offer PhD programs and in which disciplines?",
        "ground_truth": {
            "key_facts": ["PhD", "QIP", "Computer Science", "Mechanical", "Civil", "Electrical"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-PROG-004",
        "category": "Academic Programs",
        "query": "Are BBA and BCA courses available at GNDEC?",
        "ground_truth": {
            "key_facts": ["BBA", "BCA", "Computer Applications", "Business Administration"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },

    # =========================================================================
    # 5. CAMPUS FACILITIES, HOSTELS & LIFE
    # =========================================================================
    {
        "id": "GOLD-FACIL-001",
        "category": "Campus Facilities",
        "query": "Tell me about hostel accommodation for boys and girls at GNDEC.",
        "ground_truth": {
            "key_facts": ["Hostel", "Boys", "Girls", "Mess", "Rooms"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-FACIL-002",
        "category": "Campus Facilities",
        "query": "What are the features and resources of the Central Library?",
        "ground_truth": {
            "key_facts": ["Library", "Books", "Journals", "e-resources", "Reading"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-FACIL-003",
        "category": "Campus Facilities",
        "query": "What sports and fitness facilities are present on campus?",
        "ground_truth": {
            "key_facts": ["Gymnasium", "Ground", "Swimming Pool", "Sports"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-FACIL-004",
        "category": "Campus Facilities",
        "query": "Is there a health center or dispensary inside GNDEC?",
        "ground_truth": {
            "key_facts": ["Dispensary", "Medical", "Doctor", "Health"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-FACIL-005",
        "category": "Campus Facilities",
        "query": "Is there a Gurdwara Sahib on the college campus?",
        "ground_truth": {
            "key_facts": ["Gurdwara", "Campus", "Nankana Sahib"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },

    # =========================================================================
    # 6. PLACEMENTS & TRAINING (T&P)
    # =========================================================================
    {
        "id": "GOLD-TNP-001",
        "category": "Placements & Training",
        "query": "Which major companies recruit from GNDEC Training and Placement cell?",
        "ground_truth": {
            "key_facts": ["TCS", "Infosys", "Cognizant", "Wipro", "Placement"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-TNP-002",
        "category": "Placements & Training",
        "query": "Who is the Training and Placement Officer (TPO) at GNDEC?",
        "ground_truth": {
            "key_facts": ["Training and Placement", "tpo@gndec.ac.in"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-TNP-003",
        "category": "Placements & Training",
        "query": "What placement assistance and pre-placement training does the college provide?",
        "ground_truth": {
            "key_facts": ["Training", "Internship", "Placement", "Mock", "Interview"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },

    # =========================================================================
    # 7. INSTITUTIONAL OVERVIEW & ACCREDITATION
    # =========================================================================
    {
        "id": "GOLD-INST-001",
        "category": "Institutional Overview",
        "query": "When was GNDEC established and who manages the college?",
        "ground_truth": {
            "key_facts": ["1953", "Nankana Sahib Education Trust", "NSET"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-INST-002",
        "category": "Institutional Overview",
        "query": "Who laid the foundation stone of GNDEC Ludhiana?",
        "ground_truth": {
            "key_facts": ["Dr. Rajendra Prasad", "1956"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-INST-003",
        "category": "Institutional Overview",
        "query": "Is GNDEC an autonomous college and which university is it affiliated to?",
        "ground_truth": {
            "key_facts": ["Autonomous", "Punjab Technical University", "IKGPTU"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-INST-004",
        "category": "Institutional Overview",
        "query": "What is the NAAC accreditation grade of GNDEC?",
        "ground_truth": {
            "key_facts": ["NAAC", "A"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-INST-005",
        "category": "Institutional Overview",
        "query": "What is the address and location of GNDEC?",
        "ground_truth": {
            "key_facts": ["Gill Park", "Gill Road", "Ludhiana", "Punjab", "141006"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },

    # =========================================================================
    # 8. MULTILINGUAL & REGIONAL QUERIES
    # =========================================================================
    {
        "id": "GOLD-LANG-001",
        "category": "Multilingual Handling",
        "query": "btech di fees kinni aa gndec vich?",
        "ground_truth": {
            "key_facts": ["68429", "B.Tech"],
            "must_contain_tables": True,
            "prohibited": ["I do not have information"],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-LANG-002",
        "category": "Multilingual Handling",
        "query": "ਕਾਲਜ ਵਿੱਚ ਦਾਖਲਾ ਲੈਣ ਲਈ ਕੀ ਯੋਗਤਾ ਹੈ?",
        "ground_truth": {
            "key_facts": ["ਦਾਖਲਾ", "ਯੋਗਤਾ"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-LANG-003",
        "category": "Multilingual Handling",
        "query": "GNDEC me CSE department ke HOD kaun hain?",
        "ground_truth": {
            "key_facts": ["Kiran Jyoti", "kiranjyotibains@gndec.ac.in"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-LANG-004",
        "category": "Multilingual Handling",
        "query": "mtech di 1st semester di fees kinni hai?",
        "ground_truth": {
            "key_facts": ["60839", "M.Tech"],
            "must_contain_tables": True,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-LANG-005",
        "category": "Multilingual Handling",
        "query": "ਕਿਹੜੇ-ਕਿਹੜੇ ਪ੍ਰੋਗਰਾਮ GNDEC ਵਿੱਚ ਪੜ੍ਹਾਏ ਜਾਂਦੇ ਹਨ?",
        "ground_truth": {
            "key_facts": ["B.Tech", "M.Tech", "MBA", "MCA"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },
    {
        "id": "GOLD-LANG-006",
        "category": "Multilingual Handling",
        "query": "kya gndec me boys hostel available hai?",
        "ground_truth": {
            "key_facts": ["Hostel", "Boys"],
            "must_contain_tables": False,
            "prohibited": [],
            "should_abstain": False
        }
    },

    # =========================================================================
    # 9. OUT-OF-DOMAIN & DOMAIN GUARDRAILS (Strict Rejection)
    # =========================================================================
    {
        "id": "GOLD-OOD-001",
        "category": "Domain Guardrails",
        "query": "Write a Python script to do binary search on an array",
        "ground_truth": {
            "key_facts": ["only have knowledge about GNDEC"],
            "must_contain_tables": False,
            "prohibited": ["def binary_search", "class BinarySearch", "mid = "],
            "should_abstain": True
        }
    },
    {
        "id": "GOLD-OOD-002",
        "category": "Domain Guardrails",
        "query": "What is the capital city of Australia?",
        "ground_truth": {
            "key_facts": ["only have knowledge about GNDEC"],
            "must_contain_tables": False,
            "prohibited": ["Canberra", "Sydney", "Melbourne"],
            "should_abstain": True
        }
    },
    {
        "id": "GOLD-OOD-003",
        "category": "Domain Guardrails",
        "query": "Solve this equation: 4x^2 + 12x + 9 = 0",
        "ground_truth": {
            "key_facts": ["only have knowledge about GNDEC"],
            "must_contain_tables": False,
            "prohibited": ["x = -3/2", "x = -1.5"],
            "should_abstain": True
        }
    },
    {
        "id": "GOLD-OOD-004",
        "category": "Domain Guardrails",
        "query": "What is the fee structure of IIT Bombay computer science?",
        "ground_truth": {
            "key_facts": ["only have knowledge about GNDEC"],
            "must_contain_tables": False,
            "prohibited": ["IIT Bombay fees", "Powai"],
            "should_abstain": True
        }
    },
    {
        "id": "GOLD-OOD-005",
        "category": "Domain Guardrails",
        "query": "Explain quantum entanglement in physics",
        "ground_truth": {
            "key_facts": ["only have knowledge about GNDEC"],
            "must_contain_tables": False,
            "prohibited": ["EPR paradox", "quantum state", "qubits"],
            "should_abstain": True
        }
    },

    # =========================================================================
    # 10. UNANSWERABLE / HONEST ABSTENTION (Zero Hallucination)
    # =========================================================================
    {
        "id": "GOLD-ABSTAIN-001",
        "category": "Honest Abstention",
        "query": "What is the personal mobile phone number of the principal's driver?",
        "ground_truth": {
            "key_facts": ["I do not have information", "not available", "contact the college"],
            "must_contain_tables": False,
            "prohibited": ["+91 987", "+91 981"],
            "should_abstain": True
        }
    },
    {
        "id": "GOLD-ABSTAIN-002",
        "category": "Honest Abstention",
        "query": "What will be the exact lunch menu in Hostel No. 1 next Wednesday?",
        "ground_truth": {
            "key_facts": ["I do not have information", "not available", "hostel"],
            "must_contain_tables": False,
            "prohibited": ["Dal Makhani", "Paneer Butter Masala", "Rajma Chawal"],
            "should_abstain": True
        }
    },
    {
        "id": "GOLD-ABSTAIN-003",
        "category": "Honest Abstention",
        "query": "What is the private password for GNDEC campus WiFi network?",
        "ground_truth": {
            "key_facts": ["I do not have information", "not available", "contact the network"],
            "must_contain_tables": False,
            "prohibited": ["password123", "gndec@123", "wifi2026"],
            "should_abstain": True
        }
    },
]

def main():
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "gold_set.jsonl")

    with open(out_path, "w", encoding="utf-8") as f:
        for item in GOLD_ITEMS:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"✅ Generated {len(GOLD_ITEMS)} stratified Gold Standard test cases at: {out_path}")

if __name__ == "__main__":
    main()
