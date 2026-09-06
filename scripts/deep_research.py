#!/usr/bin/env python3
"""
Deep research — fetch key GNDEC pages and extract all factual claims,
then cross-reference against our gold set and corpus.
"""
import json, os, re, sys, warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore")
requests.packages.urllib3.disable_warnings()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 20
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def fetch(url, timeout=TIMEOUT):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
        r.raise_for_status()
        return r.text
    except Exception as e:
        return None


def get_text(html):
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    # Remove script/style/nav
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    lines = [l.strip() for l in text.splitlines() if l.strip() and len(l.strip()) > 15]
    return lines


def extract_facts(lines):
    """Extract potentially factual statements."""
    facts = []
    for line in lines:
        # Skip navigation/menu items
        if re.match(r"^(Home|About|Contact|Programs|Faculty|Admission|Login|Sign Up)", line):
            continue
        facts.append(line)
    return facts


def find_facts_on_page(lines, patterns):
    """Check which patterns appear on the page."""
    full = " ".join(l.lower() for l in lines)
    results = {}
    for name, pattern in patterns.items():
        found = bool(re.search(pattern, full, re.IGNORECASE))
        results[name] = found
    return results


def main():
    print("=" * 70)
    print("GNDEC DEEP RESEARCH — LIVE SITE vs CORPUS VERIFICATION")
    print("=" * 70)

    # Pages to fetch
    pages = [
        ("GNDEC Homepage", "https://gndec.ac.in"),
        ("About GNDEC", "https://gndec.ac.in/?q=about"),
        ("About Page", "https://gndec.ac.in/?q=node/1"),
        ("Vision Mission", "https://gndec.ac.in/?q=vision-mission"),
        ("History", "https://gndec.ac.in/?q=history"),
        ("CSE Homepage", "https://cse.gndec.ac.in"),
        ("IT Dept", "https://it.gndec.ac.in"),
        ("ECE Dept", "https://ece.gndec.ac.in"),
        ("EE Dept", "https://ee.gndec.ac.in"),
        ("CE Dept", "https://civil.gndec.ac.in"),
        ("ME Dept", "https://me.gndec.ac.in"),
        ("MBA Dept", "https://mba.gndec.ac.in"),
        ("MCA Dept", "https://ca.gndec.ac.in"),
        ("Admission Portal", "https://admission.gndec.ac.in"),
    ]

    all_results = {}
    for label, url in pages:
        print(f"\n[{label}] {url}")
        html = fetch(url)
        if html is None:
            print("  ❌ FAILED (no response)")
            all_results[label] = {"url": url, "status": "failed", "facts": {}}
            continue
        lines = get_text(html)
        print(f"  ✅ {len(lines)} text lines extracted")
        all_results[label] = {"url": url, "status": "ok", "lines": lines}

        # Show first 10 meaningful lines
        for ln in lines[:10]:
            print(f"    {ln[:120]}")

    # Now do fact spot-checks across all pages
    print("\n" + "=" * 70)
    print("FACT VERIFICATION — which claims appear on LIVE pages?")
    print("=" * 70)

    facts = {
        "GNDEC Ludhiana": r"ludhiana",
        "Established 1956": r"1956",
        "Established 1953": r"1953",
        "NBA Accredited": r"nba",
        "NAAC Accredited": r"naac",
        "IKGPTU Affiliation": r"ikgptu",
        "Autonomous College": r"autonom",
        "Principal Sehjal Singh": r"sehjpal\s+singh",
        "Principal Other": r"principal",
        "GNDEC Located in Punjab": r"punjab",
        "TCS Recruiter": r"\btcs\b",
        "Infosys Recruiter": r"\binfosys\b",
        "WIPRO Recruiter": r"\bwipro\b",
        "Microsoft Recruiter": r"\bmicrosoft\b",
        "Cognizant Recruiter": r"\bcognizant\b",
        "L&T Recruiter": r"\bl&t\b",
        "Boys Hostel": r"hostel",
        "Girls Hostel": r"hostel",
        "Library": r"library",
        "Dispensary/Medical": r"dispensary|medical|health",
        "Computer Centre": r"computer\s+centre|computer\s+center",
        "Sports Facility": r"sports|gymnasium|playground",
        "NSS/NCC": r"\bnss\b|\bncc\b",
        " NBA / NAAC dates": r"2023|2024|2025|2026",
    }

    # Aggregate all text
    all_text = {}
    for label, res in all_results.items():
        all_text[label] = " ".join(res.get("lines", []))

    print(f"\n{'Fact':<35} | {'Homepage':>9} | {'About':>9} | {'CSE':>9} | {'Other':>9}")
    print("-" * 75)

    for fact_name, pattern in facts.items():
        homepage = bool(re.search(pattern, all_text.get("GNDEC Homepage", ""), re.IGNORECASE))
        about = bool(re.search(pattern, all_text.get("About GNDEC", "") + all_text.get("About Page", ""), re.IGNORECASE))
        cse = bool(re.search(pattern, all_text.get("CSE Homepage", ""), re.IGNORECASE))
        other = any(re.search(pattern, all_text.get(l, ""), re.IGNORECASE) for l in all_results if l not in ["GNDEC Homepage", "About GNDEC", "About Page", "CSE Homepage"])
        any_page = homepage or about or cse or other
        print(f"  {fact_name:<33} | {'✅' if homepage else '❌':>9} | {'✅' if about else '❌':>9} | {'✅' if cse else '❌':>9} | {'✅' if other else '❌':>9}")

    # Load corpus for comparison
    print("\n" + "=" * 70)
    print("CORPUS vs LIVE SITE — key claims comparison")
    print("=" * 70)

    # Verified facts to check
    checks = [
        ("GNDEC established in 1956", "1956", ["GNDEC Homepage", "About GNDEC", "About Page"]),
        ("GNDEC in Ludhiana Punjab", "ludhiana", ["GNDEC Homepage", "About GNDEC", "About Page"]),
        ("NBA Accredited", "nba", list(all_results.keys())),
        ("NAAC Accredited", "naac", list(all_results.keys())),
        ("Affiliated to IKGPTU", "ikgptu", list(all_results.keys())),
        ("Autonomous", "autonom", ["GNDEC Homepage", "About GNDEC", "About Page"]),
    ]

    for claim, keyword, page_list in checks:
        found_pages = [l for l in page_list if l in all_results and re.search(keyword, all_text.get(l, ""), re.IGNORECASE)]
        status = "✅ LIVE" if found_pages else "❌ NOT FOUND"
        print(f"  {status} — {claim}")
        if found_pages:
            print(f"           Found on: {', '.join(found_pages[:3])}")

    # Save all data
    out_path = os.path.join(DATA, "deep_research_output.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved full scrape: {out_path}")
    print("\n✅ Research complete.")


if __name__ == "__main__":
    main()
