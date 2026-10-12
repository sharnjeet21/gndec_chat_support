"""
scripts/scrape_notices.py — Scraper for GNDEC Official Notices & Announcements
=============================================================================
Fetches the latest notices, circulars, and PDF announcements from GNDEC portals:
- Main Website: https://gndec.ac.in/
- Admission Portal: https://admission.gndec.ac.in/important_notices.php
- Academic Portal: https://academics.gndec.ac.in/
- Exam & Fee Notices: https://gndec.ac.in/?q=fee_notice

Extracts text from web announcements and attached PDF documents via PyMuPDF (fitz),
structuring them into normalized Q&A pairs for the GNDEC RAG vector store.

Run:
    python3 scripts/scrape_notices.py
"""

import os
import re
import json
import logging
import urllib3
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(ROOT_DIR, "data", "notices.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
}

NOTICE_SOURCES = [
    {"url": "https://gndec.ac.in/", "name": "GNDEC Homepage Alerts"},
    {"url": "https://gndec.ac.in/?q=fee_notice", "name": "Fee Notices"},
    {"url": "https://admission.gndec.ac.in/important_notices.php", "name": "Admission Notices"},
    {"url": "https://academics.gndec.ac.in/", "name": "Academics Portal"},
]

def clean_text(text: str) -> str:
    """Clean extra spaces and line breaks."""
    if not text:
        return ""
    t = re.sub(r'\s+', ' ', text)
    return t.strip()

def extract_pdf_text(pdf_url: str, max_pages: int = 5) -> str:
    """Download and extract clean text from a notice PDF."""
    if not fitz:
        return ""
    try:
        r = requests.get(pdf_url, headers=HEADERS, timeout=12, verify=False)
        if r.status_code != 200 or len(r.content) < 500:
            return ""

        doc = fitz.open(stream=r.content, filetype="pdf")
        pages_text = []
        for i in range(min(len(doc), max_pages)):
            pages_text.append(doc[i].get_text())

        full_text = "\n".join(pages_text)
        # Clean up scanned or hyphenated linebreaks
        cleaned = re.sub(r'(\w+)-\n(\w+)', r'\1\2', full_text)
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        cleaned = re.sub(r'\n\s*\n+', '\n\n', cleaned)
        return cleaned.strip()
    except Exception as e:
        logging.warning(f"Could not extract PDF {pdf_url}: {e}")
        return ""

def scrape_gndec_notices() -> list:
    """Scrape notices from known portals and parse PDF attachments."""
    all_notices = []
    seen_urls = set()

    for src in NOTICE_SOURCES:
        url = src["url"]
        portal_name = src["name"]
        logging.info(f"🔍 Scraping notice source: {portal_name} ({url})")

        try:
            r = requests.get(url, headers=HEADERS, timeout=12, verify=False)
            if r.status_code != 200:
                logging.warning(f"Failed to fetch {url} (Status: {r.status_code})")
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            links = soup.find_all("a", href=True)

            for link in links:
                href = link["href"].strip()
                text = clean_text(link.get_text())

                # Check if it's a notice link
                abs_url = urljoin(url, href)
                if abs_url in seen_urls:
                    continue

                is_notice = (
                    "notice" in text.lower() or
                    "circular" in text.lower() or
                    "counselling" in text.lower() or
                    "scholarship" in text.lower() or
                    "datesheet" in text.lower() or
                    "admission" in text.lower() or
                    "fee" in text.lower() or
                    "/sites/default/files/" in href.lower() or
                    "important_notices" in href.lower()
                )

                if not is_notice or len(text) < 5:
                    continue

                seen_urls.add(abs_url)

                # Extract details
                pdf_content = ""
                if abs_url.lower().endswith(".pdf"):
                    pdf_content = extract_pdf_text(abs_url)

                if pdf_content:
                    answer_text = (
                        f"Official Notice Title: {text}\n"
                        f"Portal Source: {portal_name}\n"
                        f"Document URL: {abs_url}\n\n"
                        f"Notice Details:\n{pdf_content[:2500]}"
                    )
                else:
                    answer_text = (
                        f"Official Notice: {text}\n"
                        f"Source Section: {portal_name}\n"
                        f"Official Link: {abs_url}\n"
                        f"For complete information and updates, visit the official portal: {abs_url}"
                    )

                question = f"What is the official notice regarding {text}? What are the latest updates about {text} at GNDEC?"

                all_notices.append({
                    "question": question,
                    "answer": answer_text,
                    "section": "Latest Notices & Circulars",
                    "source_file": "gndec.ac.in",
                    "doc_url": abs_url
                })
                logging.info(f"  ✅ Added notice: {text[:60]} (PDF: {bool(pdf_content)})")

        except Exception as e:
            logging.error(f"Error scraping {url}: {e}")

    # Deduplicate and sort
    logging.info(f"✨ Successfully scraped {len(all_notices)} notices and circulars.")
    return all_notices

def main():
    notices = scrape_gndec_notices()
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(notices, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(notices)} notices to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
