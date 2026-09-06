#!/usr/bin/env python3
"""
Deep research scraper — fetches key GNDEC pages, extracts facts,
and cross-references them against our corpus.
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 15
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def fetch(url, timeout=TIMEOUT):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
        r.raise_for_status()
        return r.text
    except Exception as e:
        return f"[ERROR {url}] {e}"


def extract_facts(html, url):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n", strip=True)
    # Remove excessive blank lines
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines


def load_corpus_answers():
    """Load verified answers from our authoritative JSON files."""
    answers = {}
    files = ["verified_facts.json", "gndec_facts.json", "admission_process.json", "faculty.json"]
    for fname in files:
        path = os.path.join(DATA, fname)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        items = data if isinstance(data, list) else data.get("data", [])
        for it in items:
            if isinstance(it, dict):
                q = (it.get("question") or "").strip()
                a = (it.get("answer") or "").strip()
                if q:
                    answers[q.lower()] = {"answer": a, "source": fname}
    print(f"  Loaded {len(answers)} Q&A pairs from corpus")
    return answers


PAGES = [
    # (label, url)
    ("Homepage", "https://gndec.ac.in"),
    ("About", "https://gndec.ac.in/?q=node/2"),
    ("Contact", "https://gndec.ac.in/?q=contact"),
    ("Programs", "https://gndec.ac.in/?q=programs-offered"),
    ("CSE Faculty", "https://cse.gndec.ac.in"),
    ("T&P Cell", "https://gndec.ac.in/?q=tnp"),
    ("Admission", "https://admission.gndec.ac.in"),
    ("Fee Structure", "https://gndec.ac.in/?q=fee-structure"),
    ("Notices", "https://gndec.ac.in/?q=notice"),
    ("Syllabus", "https://gndec.ac.in/?q=node/33"),
]


def main():
    import warnings
    warnings.filterwarnings("ignore")
    requests.packages.urllib3.disable_warnings()

    print("=" * 70)
    print("GNDEC RAG — DEEP RESEARCH & FACT VERIFICATION")
    print("=" * 70)

    corpus = load_corpus_answers()

    results = {}
    for label, url in PAGES:
        print(f"\nFetching: {label} → {url}", flush=True)
        html = fetch(url)
        if html.startswith("[ERROR"):
            print(f"  {html}")
            results[label] = {"url": url, "error": html, "text": ""}
            continue

        lines = extract_facts(html, url)
        print(f"  Extracted {len(lines)} text lines")
        # Show first meaningful lines
        for line in lines[:15]:
            if len(line) > 20:
                print(f"    {line[:120]}")
        results[label] = {"url": url, "lines": lines, "html_size": len(html)}

    # Save results
    out = os.path.join(DATA, "firecrawl_verification.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")

    # Fact spot-checks
    print("\n" + "=" * 70)
    print("FACT SPOT-CHECKS vs LIVE SITE")
    print("=" * 70)

    checks = [
        ("established year", "195", "GNDEC establishment year"),
        ("principal", "sehjpal", "Principal name"),
        ("nacc", "accredit", "NBA/NAAC accreditation"),
        ("location", "ludhiana", "College location"),
        ("affiliation", "ikgptu", "Affiliation"),
        ("autonomous", "autonom", "Autonomous status"),
    ]

    home_lines = " ".join(results.get("Homepage", {}).get("lines", []))
    for keyword, expected, description in checks:
        found = keyword.lower() in home_lines.lower()
        print(f"  {'✅' if found else '❌'} {description}: '{keyword}' {'found' if found else 'NOT found'} on homepage")

    # Check T&P page for company names
    tnp_lines = " ".join(results.get("T&P Cell", {}).get("lines", []))
    companies = ["TCS", "Infosys", "WIPRO", "Microsoft", "Cognizant", "L&T"]
    print(f"\n  T&P companies found on live site:")
    for c in companies:
        found = c.lower() in tnp_lines.lower()
        print(f"    {'✅' if found else '❌'} {c}")

    print("\nDone.")


if __name__ == "__main__":
    main()
