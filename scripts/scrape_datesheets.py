"""
scripts/scrape_datesheets.py — Scraper for GNDEC Datesheets, Calendars & Exam Schedules
========================================================================================
Extracts examination datesheets, mid-semester test (MST) schedules, end-semester
examinations (ESE), and academic calendars from GNDEC portals.

Run:
    python3 scripts/scrape_datesheets.py
"""

import os
import re
import json
import logging
import urllib3
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

try:
    import fitz
except ImportError:
    fitz = None

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(ROOT_DIR, "data", "datesheets.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
}

DATESHEET_SOURCES = [
    {"url": "https://gndec.ac.in/?q=datesheet", "name": "Datesheets Section"},
    {"url": "https://gndec.ac.in/?q=examination", "name": "Examination Cell"},
    {"url": "https://academics.gndec.ac.in/", "name": "Student Academics & Exam Portal"},
    {"url": "https://exam.gndec.ac.in/", "name": "Staff Examination Portal"},
]

def clean_text(text: str) -> str:
    if not text:
        return ""
    t = re.sub(r'\s+', ' ', text)
    return t.strip()

def extract_pdf_content(pdf_url: str, max_pages: int = 5) -> str:
    if not fitz:
        return ""
    try:
        r = requests.get(pdf_url, headers=HEADERS, timeout=12, verify=False)
        if r.status_code != 200 or len(r.content) < 500:
            return ""
        doc = fitz.open(stream=r.content, filetype="pdf")
        pages = [doc[i].get_text() for i in range(min(len(doc), max_pages))]
        full_text = "\n".join(pages)
        cleaned = re.sub(r'[ \t]+', ' ', full_text)
        cleaned = re.sub(r'\n\s*\n+', '\n\n', cleaned)
        return cleaned.strip()
    except Exception as e:
        logging.warning(f"Could not extract datesheet PDF {pdf_url}: {e}")
        return ""

def scrape_datesheets() -> list:
    records = []
    seen = set()

    for src in DATESHEET_SOURCES:
        url = src["url"]
        name = src["name"]
        logging.info(f"📅 Checking datesheet source: {name} ({url})")

        try:
            r = requests.get(url, headers=HEADERS, timeout=12, verify=False)
            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            for link in soup.find_all("a", href=True):
                href = link["href"].strip()
                text = clean_text(link.get_text())
                abs_url = urljoin(url, href)

                if abs_url in seen:
                    continue

                is_exam = any(k in text.lower() or k in href.lower() for k in [
                    "datesheet", "date sheet", "examination", "exam schedule",
                    "mst", "mid semester", "end semester", "ese", "academic calendar"
                ])

                if not is_exam or len(text) < 4:
                    continue

                seen.add(abs_url)
                pdf_text = ""
                if abs_url.lower().endswith(".pdf"):
                    pdf_text = extract_pdf_content(abs_url)

                if pdf_text:
                    ans = (
                        f"Official Examination / Datesheet Information: {text}\n"
                        f"Source Portal: {name}\n"
                        f"Document Link: {abs_url}\n\n"
                        f"Schedule Details:\n{pdf_text[:2500]}"
                    )
                else:
                    ans = (
                        f"Official Examination / Datesheet: {text}\n"
                        f"Source: {name}\n"
                        f"Portal Link: {abs_url}\n"
                        f"Students can check their individual exam schedules and room allocations on the academics portal: https://academics.gndec.ac.in/"
                    )

                q = f"What is the exam datesheet or schedule for {text} at GNDEC?"
                records.append({
                    "question": q,
                    "answer": ans,
                    "section": "Examination Datesheets & Schedules",
                    "source_file": "gndec.ac.in",
                    "doc_url": abs_url
                })
                logging.info(f"  ✅ Added datesheet entry: {text[:60]}")

        except Exception as e:
            logging.error(f"Error checking {url}: {e}")

    # Standard general FAQ for examination and datesheets
    records.append({
        "question": "How can GNDEC students access their examination datesheet and academic calendar?",
        "answer": (
            "GNDEC students can access their examination datesheets, mid-semester test (MST) schedules, "
            "and end-semester examination (ESE) seating plans via the official Student Academic Portal at "
            "https://academics.gndec.ac.in/ or the main website notice board at https://gndec.ac.in/?q=datesheet."
        ),
        "section": "Examination Datesheets & Schedules",
        "source_file": "gndec.ac.in",
        "doc_url": "https://academics.gndec.ac.in/"
    })

    return records

def main():
    items = scrape_datesheets()
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(items)} datesheet records to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
