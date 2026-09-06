"""
Structured Admission Process Routing — Fix Timeout Failures
Handles: admission process, entrance exam, application procedures
"""
import json
from pathlib import Path

# Load admission process data
admission_data = {
    "how_to_apply": {
        "question": "How to apply for B.Tech admission at GNDEC?",
        "answer": """The B.Tech admission process at GNDEC follows these steps:

1. **JEE Main Exam**: Appear for JEE Main examination conducted by NTA.

2. **Centralized Counseling**: Register for Punjab State counseling conducted by Punjab Technical University (IKGPTU) or All India counseling (15% quota).

3. **Online Registration**: Fill the online application form on the official counseling portal with JEE Main rank and personal details.

4. **Choice Filling**: Select GNDEC Ludhiana and preferred branches (CSE, IT, ME, CE, EE, ECE, PE) in order of preference.

5. **Seat Allotment**: Based on JEE Main rank, category, and quota, seats are allotted through multiple counseling rounds.

6. **Document Verification**: Report to GNDEC with original documents for physical verification during the allotted time slot.

7. **Fee Payment**: Pay the admission fee online or at the college counter to confirm admission.

8. **Final Admission**: Complete remaining formalities and receive admission confirmation.

Visit admission.gndec.ac.in for detailed instructions and counseling schedule.""",
        "section": "Admissions Process",
        "source_file": "admission.gndec.ac.in"
    },

    "entrance_exam": {
        "question": "Is there any entrance exam for GNDEC admission? What entrance exam is required?",
        "answer": """Yes, entrance exams are required for admission to GNDEC:

**For B.Tech 1st Year:**
- **JEE Main** is mandatory for all candidates
- Conducted by NTA (National Testing Agency)
- Admission is through centralized counseling based on JEE Main rank

**For B.Tech Lateral Entry (LEET):**
- Direct admission based on Diploma/B.Sc. marks
- No separate entrance exam required
- Merit-based admission through PTU counseling

**For M.Tech:**
- **GATE score** preferred (first preference in counseling)
- Non-GATE candidates admitted based on B.Tech marks

**For MBA:**
- **CMAT score** required
- Admission through PTU counseling

**For MCA:**
- Merit-based on qualifying degree marks
- No separate entrance exam

All admissions follow centralized counseling by Punjab Technical University (IKGPTU).""",
        "section": "Entrance Exams",
        "source_file": "admission.gndec.ac.in"
    },

    "gate_requirement": {
        "question": "Do I need GATE score for M.Tech admission at GNDEC?",
        "answer": """GATE score is **preferred but not mandatory** for M.Tech admission at GNDEC:

**With GATE Score:**
- First preference during counseling
- Better chance of getting preferred branch
- Required for AICTE/MHRD scholarship eligibility

**Without GATE Score:**
- Admission possible based on B.Tech/B.E. marks
- Must have minimum 50% marks (45% for reserved categories)
- Admitted through PTU counseling on merit basis
- Lower priority compared to GATE candidates

**Recommendation:** While GATE is not mandatory, having a valid GATE score significantly improves your chances of admission and scholarship eligibility.""",
        "section": "M.Tech Admissions",
        "source_file": "admission.gndec.ac.in"
    },

    "admission_process": {
        "question": "What is the admission process at GNDEC?",
        "answer": """The admission process at GNDEC follows these steps:

**For B.Tech:**
1. Qualify JEE Main examination
2. Register for Punjab State or All India counseling
3. Fill online application with rank and preferences
4. Attend counseling rounds and choice filling
5. Seat allotment based on rank and category
6. Document verification at GNDEC
7. Fee payment to confirm admission

**For Lateral Entry (LEET):**
1. Complete 3-year Diploma with 45% marks (40% reserved)
2. Register for PTU LEET counseling
3. Choice filling and seat allotment
4. Document verification and fee payment

**For M.Tech:**
1. GATE qualified or B.Tech 50%+ marks
2. PTU counseling registration
3. Branch-wise seat allotment
4. Admission confirmation at GNDEC

All admissions conducted through centralized counseling by Punjab Technical University (IKGPTU). Visit admission.gndec.ac.in for detailed schedule and guidelines.""",
        "section": "Admissions Process",
        "source_file": "admission.gndec.ac.in"
    }
}

# Save to JSON
output_file = Path(__file__).parent / "data" / "admission_process.json"
output_file.parent.mkdir(exist_ok=True)

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(list(admission_data.values()), f, indent=2, ensure_ascii=False)

print(f"Created: {output_file}")
print(f"Added {len(admission_data)} admission process Q&A entries")
