#!/usr/bin/env python3
"""
scrape_full_faculty.py — Scrapes comprehensive faculty details for all GNDEC departments
Directly extracts every department and individual faculty profile from https://gndec.ac.in/faculty/
"""

import json
import os
import re
import urllib3
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://gndec.ac.in/faculty/"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

DEPTS = {
    1: "Applied Science",
    2: "Computer Center",
    3: "Workshops",
    4: "Sports",
    14: "Civil Engineering",
    15: "Computer Science & Engg.",
    16: "Electrical Engineering",
    17: "Electronics & Communication Engineering",
    21: "Information Technology",
    28: "Business Administration",
    29: "Computer Applications",
    30: "Mechanical Engineering",
    31: "Production Engineering",
    99: "School of Architecture",
}

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def scrape_faculty_profile(item: dict) -> dict:
    """Scrapes individual faculty profile details from id URL if present."""
    profile_url = item.get("profile_url")
    if not profile_url:
        return item

    try:
        r = requests.get(profile_url, timeout=10, verify=False)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for table in soup.find_all("table"):
                for row in table.find_all("tr"):
                    cols = [c.text.strip() for c in row.find_all(["th", "td"])]
                    if len(cols) >= 2:
                        k, v = cols[0].lower(), cols[1]
                        if "experience" in k and not item.get("experience"):
                            item["experience"] = clean_text(v)
                        elif "qualification" in k and not item.get("qualification"):
                            item["qualification"] = clean_text(v)
                        elif "journal" in k and not item.get("publications_journal"):
                            item["publications_journal"] = clean_text(v)
                        elif "conference" in k and not item.get("publications_conference"):
                            item["publications_conference"] = clean_text(v)
                        elif "membership" in k and not item.get("memberships"):
                            item["memberships"] = clean_text(v)
                        elif "research" in k and not item.get("research_interest"):
                            item["research_interest"] = clean_text(v)
    except Exception as e:
        pass

    return item

def scrape_all_departments():
    print("=" * 80)
    print("SCRAPING ALL FACULTY & STAFF FROM https://gndec.ac.in/faculty/")
    print("=" * 80)

    all_members = []

    for dept_id, dept_name in DEPTS.items():
        url = f"{BASE_URL}?deptt={dept_id}"
        try:
            r = requests.get(url, timeout=12, verify=False)
            if r.status_code != 200:
                print(f"⚠️  Failed to fetch dept {dept_id}: {dept_name}")
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            table = soup.find("table")
            if not table:
                print(f"⚠️  No table found for dept {dept_id}: {dept_name}")
                continue

            dept_members = []
            for row in table.find_all("tr"):
                cols = row.find_all(["th", "td"])
                if not cols or len(cols) < 3:
                    continue

                # Header row check
                first_col = cols[0].text.strip().lower()
                if "name" in first_col:
                    continue

                name = clean_text(cols[0].text)
                designation = clean_text(cols[1].text)
                email = clean_text(cols[2].text)

                if not name:
                    continue

                # Extract Links
                profile_url = ""
                vidwan_url = ""
                for a in row.find_all("a"):
                    href = a.get("href", "")
                    if "?id=" in href:
                        if not href.startswith("http"):
                            href = f"https://gndec.ac.in/faculty/{href}" if not href.startswith("/") else f"https://gndec.ac.in{href}"
                        profile_url = href
                    elif "vidwan" in href:
                        vidwan_url = href

                member_record = {
                    "department": dept_name,
                    "name": name,
                    "designation": designation,
                    "email": email,
                    "profile_url": profile_url,
                    "vidwan_url": vidwan_url,
                    "experience": "",
                    "qualification": "",
                    "publications_journal": "",
                    "publications_conference": "",
                    "memberships": "",
                    "research_interest": ""
                }
                dept_members.append(member_record)

            print(f"✓ Dept {dept_id:2d} ({dept_name}): Found {len(dept_members)} members")
            all_members.extend(dept_members)

        except Exception as e:
            print(f"❌ Error scraping dept {dept_id}: {e}")

    print(f"\nTotal faculty members found across {len(DEPTS)} departments: {len(all_members)}")
    print("Scraping detailed individual profiles concurrently...")

    enriched_members = []
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(scrape_faculty_profile, m): m for m in all_members}
        for future in as_completed(futures):
            try:
                res = future.result()
                enriched_members.append(res)
            except Exception as e:
                pass

    # Sort by department, then name
    enriched_members.sort(key=lambda x: (x["department"], x["name"]))

    # Save to data/faculty.json
    out_path = os.path.join(DATA_DIR, "faculty.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(enriched_members, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Successfully saved {len(enriched_members)} faculty profiles with full details to: {out_path}")
    return enriched_members

if __name__ == "__main__":
    scrape_all_departments()
