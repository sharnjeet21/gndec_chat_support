#!/usr/bin/env python3
"""Targeted verification of specific claims against live site."""
import json, os, re, sys, warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore")
requests.packages.urllib3.disable_warnings()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
}
DATA = "/home/sharnjeet-singh/Developer/gndec_rag/data"


def fetch_text(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20, verify=False)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        return f"[ERROR] {e}"


def search_all_pages(urls, keyword):
    """Search for a keyword across all pages."""
    results = {}
    for label, url in urls:
        text = fetch_text(url)
        if text.startswith("[ERROR]"):
            continue
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        full = " ".join(lines).lower()
        if keyword.lower() in full:
            # Find context lines
            for i, line in enumerate(lines):
                if keyword.lower() in line.lower():
                    results[label] = line.strip()[:200]
                    break
    return results


def main():
    urls = [
        ("GNDEC Homepage", "https://gndec.ac.in"),
        ("About Page", "https://gndec.ac.in/?q=node/1"),
        ("CSE Dept", "https://cse.gndec.ac.in"),
        ("IT Dept", "https://it.gndec.ac.in"),
        ("ECE Dept", "https://ece.gndec.ac.in"),
        ("EE Dept", "https://ee.gndec.ac.in"),
        ("ME Dept", "https://me.gndec.ac.in"),
        ("MBA Dept", "https://mba.gndec.ac.in"),
        ("MCA Dept", "https://ca.gndec.ac.in"),
        ("Admission Portal", "https://admission.gndec.ac.in"),
    ]

    claims = {
        "NAAC accreditation": ["naac"],
        "Infosys recruiter": ["infosys"],
        "WIPRO recruiter": ["wipro", "wipro"],
        "Dispensary on campus": ["dispensary"],
        "Gurdwara on campus": ["gurdwara"],
        "CSE established 1997": ["1997", "established in 1997"],
        "IT established 2001": ["2001", "established in 2001"],
        "ECE established 1981": ["1981", "established in 1981"],
        "EE established 1957": ["1957", "established in 1957"],
        "ME established 1957": ["1957", "established in 1957"],
        "MCA started 2009": ["2009", "started in 2009"],
        "Nankana Sahib Trust": ["nankana"],
        "NSET trust": ["nset"],
        "Autonomous": ["autonom"],
        "PhD count 148": ["148", "148 ph"],
        "TPO Gagandeep": ["gagandeep", "gagan"],
        "NIRF ranking": ["nirf"],
        "TEQIP": ["teqip"],
        "Principal name": ["sehjpal", "sejpal"],
    }

    print("TARGETED CLAIM VERIFICATION — LIVE SITE")
    print("=" * 70)

    for claim, keywords in claims.items():
        all_results = {}
        for kw in keywords:
            found = search_all_pages(urls, kw)
            all_results.update(found)
        if all_results:
            print(f"\n✅ FOUND — {claim}")
            for page, snippet in all_results.items():
                print(f"   [{page}] {snippet[:150]}")
        else:
            print(f"\n❌ NOT FOUND — {claim}")

    # Also check corpus answers for these claims
    print("\n" + "=" * 70)
    print("CORPUS ANSWERS FOR UNCONFIRMED CLAIMS")
    print("=" * 70)

    corpus_files = ["verified_facts.json", "gndec_facts.json", "tnp_data.json", "external_facts.json"]
    for fname in corpus_files:
        path = os.path.join(DATA, fname)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        items = data if isinstance(data, list) else data.get("data", [])
        for it in items:
            if not isinstance(it, dict):
                continue
            q = (it.get("question") or "").lower()
            a = (it.get("answer") or "")
            # Match relevant queries
            for claim_kw in ["naac", "infosys", "wipro", "dispensary", "gurdwara", "nankana",
                              "nset", "sehjpal", "nirf", "teqip", "148 ph"]:
                if claim_kw in q and len(a) > 20:
                    print(f"\n  [{fname}] Q: {it.get('question','')[:80]}")
                    print(f"          A: {a[:200]}")
                    break

if __name__ == "__main__":
    main()
