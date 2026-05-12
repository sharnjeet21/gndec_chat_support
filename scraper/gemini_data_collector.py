"""
GNDEC Data Collector — SERP + Ollama (local, no quota)
========================================================
1. Searches site:gndec.ac.in via SERP API for each question
2. Scrapes the top result pages for context
3. Feeds context to local Ollama (llama3.2:3b) to generate answer
4. Saves Q&A pairs to data/gndec_gemini.json

No API quotas — Ollama runs locally.
SERP API: 100 free searches/month, we use 1 per question.

Usage:  python3 scraper/gemini_data_collector.py
"""

import asyncio
import json
import os
import re
import logging
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
SERP_API_KEY  = "f2c6cc5417824ef5033c127e2b8df6fa1c152e1133294743da1590b7b8697549"
OLLAMA_URL    = "http://localhost:11434/api/generate"
OLLAMA_MODEL  = "llama3.2:3b"
OUTPUT_PATH   = "data/gndec_gemini.json"
CONCURRENCY   = 3       # parallel workers — Ollama handles concurrent fine
SERP_RESULTS  = 3       # top N search results to scrape
MAX_CONTEXT   = 3000    # chars of context to feed Ollama
TIMEOUT       = 90      # seconds per Ollama call
DELAY         = 1.0     # small delay between requests

SYSTEM = """You are an expert on Guru Nanak Dev Engineering College (GNDEC), Ludhiana, Punjab, India.
Using the context below from GNDEC official websites, answer the question accurately and completely.
Write in plain text only. No markdown, no asterisks, no bold, no # headers.
Use numbered lists (1. 2. 3.) or plain line breaks if listing items.
Be specific — include actual numbers, names, dates, phone numbers where available in the context.
If the context does not contain the answer, use your general knowledge about GNDEC."""

# ── Questions ─────────────────────────────────────────────────────────────────
QUESTIONS = [
    # General
    ("What is GNDEC Ludhiana — full name, location, establishment year, trust, and key facts?", "About GNDEC"),
    ("What is the complete history of Guru Nanak Dev Engineering College from 1956 to present?", "About GNDEC"),
    ("What is the vision, mission, and core values of GNDEC?", "About GNDEC"),
    ("What are all accreditations of GNDEC — NAAC grade, NBA programs, ISO, UGC autonomous status?", "Accreditation"),
    ("What is the NIRF ranking and other national rankings of GNDEC?", "Rankings"),
    ("What awards has GNDEC received from IKGPTU?", "Rankings"),
    ("What is the contact information, address, phone, email, and website of GNDEC?", "Contact"),
    ("What is the total student strength and faculty count at GNDEC?", "About GNDEC"),
    ("What is the campus area and infrastructure overview of GNDEC?", "Infrastructure"),

    # Programs
    ("List all B.Tech programs at GNDEC with branch names, intake seats, and NBA accreditation status.", "Programs"),
    ("List all M.Tech programs at GNDEC with specializations and intake.", "Programs"),
    ("What is the MBA program at GNDEC — duration, intake, year started, affiliation?", "Programs"),
    ("What is the MCA program at GNDEC — duration, intake, eligibility?", "Programs"),
    ("What is the BBA program at GNDEC — duration, intake, year started?", "Programs"),
    ("What is the B.Arch program at GNDEC — duration, intake, accreditation?", "Programs"),
    ("What is the B.Com Entrepreneurship program at GNDEC?", "Programs"),
    ("What is the BCA program at GNDEC?", "Programs"),
    ("What is the B.Voc Interior Design program at GNDEC?", "Programs"),
    ("What Ph.D. programs does GNDEC offer and what is the QIP centre?", "Programs"),
    ("What is the B.Tech Working Professionals program at GNDEC for CE and ME?", "Programs"),
    ("What is the lateral entry B.Tech program at GNDEC?", "Programs"),

    # Admissions
    ("What is the complete B.Tech admission process at GNDEC for 2026-27 including JEE Main and PTU counselling?", "Admissions"),
    ("What is the eligibility criteria for B.Tech admission at GNDEC — minimum marks and subjects?", "Admissions"),
    ("What is the rural area quota at GNDEC — 70% commitment, how it works, who qualifies?", "Admissions"),
    ("What are all reservation categories at GNDEC — SC/ST/OBC/EWS/sports/NCC percentages?", "Admissions"),
    ("What documents are required for B.Tech admission at GNDEC?", "Admissions"),
    ("What are all admission helpline numbers at GNDEC for 2026-27 for each program?", "Admissions"),
    ("What is the MBA admission process at GNDEC — CMAT/CAT scores, eligibility, seats?", "Admissions"),
    ("What is the MCA admission process at GNDEC — entrance exam, eligibility?", "Admissions"),
    ("What is the M.Tech admission process at GNDEC — GATE scores, CCMT counselling?", "Admissions"),
    ("What is the B.Arch admission process at GNDEC — NATA scores, eligibility?", "Admissions"),
    ("What is the Sikh Religion Examination (SRE) at GNDEC and who needs to appear?", "Admissions"),
    ("What are the typical JEE Main cut-off ranks for B.Tech CSE, IT, ECE at GNDEC?", "Admissions"),

    # Fee Structure
    ("What is the complete fee structure for B.Tech at GNDEC for session 2025-26 — all branches, general and SC/ST?", "Fee Structure"),
    ("What is the semester fee for B.Tech at GNDEC for January-June 2026?", "Fee Structure"),
    ("What is the fee structure for MBA at GNDEC per semester and total?", "Fee Structure"),
    ("What is the fee structure for MCA at GNDEC?", "Fee Structure"),
    ("What is the fee structure for M.Tech at GNDEC?", "Fee Structure"),
    ("What is the fee structure for B.Arch at GNDEC?", "Fee Structure"),
    ("What is the hostel fee at GNDEC for boys and girls hostels?", "Fee Structure"),
    ("How to pay semester fee online at GNDEC — portal, UPI, bank details?", "Fee Structure"),
    ("What is the fee difference between general and SC/ST/OBC categories at GNDEC?", "Fee Structure"),

    # Scholarships
    ("What are all scholarships available at GNDEC — government, institutional, alumni?", "Scholarships"),
    ("How to apply for Post-Matric Scholarship (PMS) at GNDEC — process, documents, helpline?", "Scholarships"),
    ("What is the alumni scholarship at GNDEC 2026 — eligibility, amount, how to apply?", "Scholarships"),
    ("What AICTE scholarships and fellowships are available for GNDEC students?", "Scholarships"),
    ("What central government scholarships can GNDEC students apply for via NSP portal?", "Scholarships"),
    ("What fee concessions are available for SC/ST students at GNDEC?", "Scholarships"),

    # Departments
    ("Describe the CSE department at GNDEC — established year, programs, labs, faculty strength, achievements.", "CSE Department"),
    ("What are the computer labs and research facilities in the CSE department at GNDEC?", "CSE Department"),
    ("Describe the IT department at GNDEC — established year, programs, HOD, labs, achievements.", "IT Department"),
    ("Describe the ECE department at GNDEC — programs, labs, IETE forum, newsletter, achievements.", "ECE Department"),
    ("Describe the EE department at GNDEC — programs, labs, power systems focus, achievements.", "EE Department"),
    ("Describe the ME department at GNDEC — programs, labs, industry connections, achievements.", "ME Department"),
    ("Describe the CE department at GNDEC — programs, labs, NBA accreditation, vision.", "CE Department"),
    ("Describe the MBA/BBA department at GNDEC — programs, intake, faculty, achievements.", "MBA Department"),
    ("Describe the MCA department at GNDEC — program, intake, labs, achievements.", "MCA Department"),
    ("Describe the Architecture department at GNDEC — program, studios, facilities.", "Architecture"),
    ("What is the Applied Sciences department at GNDEC — Physics, Chemistry, Maths faculty?", "Applied Sciences"),

    # Faculty
    ("Who is the current Principal of GNDEC and what is their background?", "Faculty"),
    ("Who are the Deans at GNDEC — Dean Academics, Dean Students Welfare, etc.?", "Faculty"),
    ("Who is the Head of CSE department at GNDEC?", "Faculty"),
    ("Who is the Head of IT department at GNDEC?", "Faculty"),
    ("Who is the Head of ECE department at GNDEC?", "Faculty"),
    ("Who is the Head of EE department at GNDEC?", "Faculty"),
    ("Who is the Head of ME department at GNDEC?", "Faculty"),
    ("Who is the Head of CE department at GNDEC?", "Faculty"),
    ("What is the faculty qualification profile at GNDEC — PhDs, publications, research?", "Faculty"),

    # Placements
    ("What is the placement record of GNDEC for 2024-25 — companies, packages, percentage?", "Placements"),
    ("What are the top companies that recruit from GNDEC campus?", "Placements"),
    ("What is the highest and average salary package at GNDEC placements?", "Placements"),
    ("What is the Training and Career Cell (TCC) at GNDEC and what does it do?", "Placements"),
    ("What pre-placement training and aptitude preparation does GNDEC provide?", "Placements"),
    ("What internship and industrial training opportunities are available at GNDEC?", "Placements"),
    ("What is the placement percentage at GNDEC for B.Tech graduates?", "Placements"),

    # Campus Life
    ("What hostel facilities are available at GNDEC — boys hostel, girls hostel, amenities, capacity?", "Hostel"),
    ("What are the hostel rules, mess facility, and fees at GNDEC?", "Hostel"),
    ("What sports facilities and achievements does GNDEC have?", "Sports"),
    ("What cultural activities, festivals, and events happen at GNDEC?", "Cultural"),
    ("What is Harmony — the annual magazine of GNDEC?", "Cultural"),
    ("What is the NCC unit at GNDEC — strength, activities, achievements?", "NCC"),
    ("What is the NSS unit at GNDEC — volunteers, activities, social service?", "NSS"),
    ("What student clubs and technical societies are active at GNDEC?", "Student Societies"),
    ("What is the Computer Society of India (CSI) chapter at GNDEC?", "Student Societies"),
    ("What is the IETE Students Forum at GNDEC ECE department?", "Student Societies"),
    ("Does GNDEC have an FM radio station — frequency, purpose?", "Campus"),
    ("What is the central library at GNDEC — books, journals, digital resources?", "Library"),
    ("What is the Knimbus digital library at GNDEC and how to access it remotely?", "Library"),
    ("What medical, canteen, and other support facilities are at GNDEC?", "Campus"),
    ("What anti-ragging measures, Shakti app, and grievance systems does GNDEC have?", "Campus"),
    ("What is the Disability Resource Centre at GNDEC?", "Campus"),

    # Exams
    ("How does the autonomous examination system work at GNDEC?", "Exams"),
    ("How to check exam results at GNDEC — portal, process?", "Exams"),
    ("What is the academic calendar at GNDEC — semester dates, exam schedule 2025-26?", "Exams"),
    ("What is the grading system and CGPA calculation at GNDEC?", "Exams"),
    ("How to get transcripts, migration certificate, and degree from GNDEC?", "Exams"),
    ("What is the ERP system at GNDEC — erp.gndec.ac.in features?", "ERP"),
    ("What is the MOOC portal at GNDEC and how to earn credits?", "MOOC"),

    # Research
    ("What research projects and funding has GNDEC received from DST, AICTE, MHRD?", "Research"),
    ("What is the TEQIP-II and TEQIP-III project at GNDEC?", "Research"),
    ("What is the QIP centre at GNDEC for Ph.D. in Civil, Mechanical, Electrical?", "Research"),

    # Alumni
    ("Who are the most notable alumni of GNDEC from Mechanical Engineering?", "Alumni"),
    ("Who are the most notable alumni of GNDEC from Electrical Engineering?", "Alumni"),
    ("Who are the most notable alumni of GNDEC from CSE and IT?", "Alumni"),
    ("Who are the most notable alumni of GNDEC from Civil Engineering?", "Alumni"),
    ("Who are the most notable alumni of GNDEC from ECE?", "Alumni"),
    ("What IAS/IPS/IFS officers are alumni of GNDEC?", "Alumni"),
    ("What GNDEC alumni are working at top companies like Apple, Microsoft, Google?", "Alumni"),
    ("What is the GNDEC alumni association and how does it support students?", "Alumni"),

    # Industry
    ("What industry MoUs and collaborations does GNDEC have?", "Industry"),
    ("What companies have signed MoUs with GNDEC for training and placements?", "Industry"),

    # Recent Events
    ("What are the latest notices and events at GNDEC for 2025-26?", "Recent Events"),
    ("What is the fee notice for GNDEC January-June 2026 — amounts for all programs?", "Recent Events"),
    ("What job openings and faculty recruitment is happening at GNDEC?", "Recent Events"),
    ("What is the GNE10 initiative at GNDEC?", "Recent Events"),
    ("What is the GNDEC e-library app and how to download it?", "Recent Events"),
    ("What is the TCC portal tnpgndec.com and what services does it offer?", "Placements"),
    ("What is the academics portal academics.gndec.ac.in?", "Exams"),
]


# ── SERP search ───────────────────────────────────────────────────────────────

async def serp_search(client: httpx.AsyncClient, question: str) -> str:
    """Search site:gndec.ac.in and return combined snippets as context."""
    try:
        r = await client.get(
            "https://serpapi.com/search.json",
            params={
                "q": f"site:gndec.ac.in {question}",
                "api_key": SERP_API_KEY,
                "num": SERP_RESULTS,
            },
            timeout=20,
        )
        r.raise_for_status()
        results = r.json().get("organic_results", [])
        parts = []
        for res in results:
            title   = res.get("title", "")
            snippet = res.get("snippet", "")
            link    = res.get("link", "")
            if snippet:
                parts.append(f"[{title}] ({link})\n{snippet}")
        return "\n\n".join(parts)[:MAX_CONTEXT]
    except Exception as e:
        logger.debug(f"SERP failed: {e}")
        return ""


# ── Ollama generation ─────────────────────────────────────────────────────────

async def ollama_generate(client: httpx.AsyncClient, question: str, context: str) -> str:
    """Generate answer using local Ollama."""
    ctx_block = f"\nContext from GNDEC websites:\n{context}\n\n" if context else "\n"
    prompt = f"{SYSTEM}{ctx_block}Question: {question}\n\nAnswer:"

    try:
        r = await client.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except Exception as e:
        logger.warning(f"  Ollama failed: {e}")
        return ""


# ── Text cleanup ──────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*",     r"\1", text)
    text = re.sub(r"^#{1,6}\s+",    "",    text, flags=re.MULTILINE)
    text = re.sub(r"`(.+?)`",        r"\1", text)
    text = re.sub(r"```[\s\S]*?```", "",    text)
    text = re.sub(r"\n{3,}",         "\n\n", text)
    return text.strip()


# ── Worker ─────────────────────────────────────────────────────────────────────

async def worker(wid: int, queue: asyncio.Queue, results: list, lock: asyncio.Lock):
    async with httpx.AsyncClient() as client:
        while True:
            try:
                idx, question, section = queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            logger.info(f"[W{wid}] {idx} {question[:65]}")

            # Step 1: Get context from SERP
            context = await serp_search(client, question)
            if context:
                logger.info(f"[W{wid}]   SERP: {len(context)} chars context")
            else:
                logger.info(f"[W{wid}]   SERP: no results, using Ollama knowledge only")

            # Step 2: Generate answer with Ollama
            answer = await ollama_generate(client, question, context)

            if answer and len(answer) > 30:
                clean = clean_text(answer)
                pair = {
                    "question":    question,
                    "answer":      clean[:3000],
                    "section":     section,
                    "source_file": "gndec.ac.in",
                }
                async with lock:
                    results.append(pair)
                    os.makedirs("data", exist_ok=True)
                    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
                        json.dump(results, f, indent=2, ensure_ascii=False)
                logger.info(f"[W{wid}] ✓ {len(clean)} chars | total={len(results)}")
            else:
                logger.warning(f"[W{wid}] ✗ No answer for: {question[:50]}")

            queue.task_done()
            await asyncio.sleep(DELAY)


# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    # Check Ollama
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get("http://localhost:11434/api/tags", timeout=5)
            models = [m["name"] for m in r.json().get("models", [])]
            if not any(OLLAMA_MODEL in m for m in models):
                logger.error(f"Model {OLLAMA_MODEL} not found. Available: {models}")
                return
        logger.info(f"✅ Ollama running with {OLLAMA_MODEL}")
    except Exception as e:
        logger.error(f"❌ Ollama not running: {e}")
        return

    # Load existing
    existing = []
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)
        logger.info(f"Resuming — {len(existing)} pairs already collected")

    existing_qs = {p["question"] for p in existing}
    results = list(existing)
    lock = asyncio.Lock()

    # Build queue
    queue: asyncio.Queue = asyncio.Queue()
    total = len(QUESTIONS)
    pending = 0
    for i, (q, section) in enumerate(QUESTIONS, 1):
        if q not in existing_qs:
            queue.put_nowait((f"{i}/{total}", q, section))
            pending += 1

    logger.info(f"Pending: {pending} | Already done: {total - pending}")

    if pending == 0:
        logger.info("All questions already collected!")
        return

    # Run workers
    workers = [
        asyncio.create_task(worker(i + 1, queue, results, lock))
        for i in range(CONCURRENCY)
    ]
    await asyncio.gather(*workers)

    logger.info(f"\n✅ Done! {len(results)} Q&A pairs saved to {OUTPUT_PATH}")
    logger.info("Next: python3 backend/build_vector_db.py")


if __name__ == "__main__":
    asyncio.run(main())
