#!/usr/bin/env python3
"""Extract key factual claims from live site scrape, cross-reference with corpus."""
import json, os, re, sys

DATA = "/home/sharnjeet-singh/Developer/gndec_rag/data"
GOLD = os.path.join(DATA, "gold_set.jsonl")

def load_gold():
    items = []
    with open(GOLD) as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items

def load_corpus():
    """Load all authoritative corpus files."""
    answers = {}
    for fname in ["verified_facts.json", "gndec_facts.json", "admission_process.json",
                  "external_facts.json", "tnp_data.json"]:
        path = os.path.join(DATA, fname)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        items = data if isinstance(data, list) else data.get("data", [])
        for it in items:
            if isinstance(it, dict):
                q = (it.get("question") or "").strip().lower()
                a = (it.get("answer") or "").strip()
                if q and a:
                    answers[q] = {"answer": a[:500], "source": fname}
    return answers

def load_live():
    path = os.path.join(DATA, "deep_research_output.json")
    if not os.path.exists(path):
        return {}
    return json.load(open(path))

def main():
    gold = load_gold()
    corpus = load_corpus()
    live = load_live()

    # Build fact -> page mapping from live site
    live_facts = {}
    for label, res in live.items():
        for line in res.get("lines", []):
            line_lc = line.lower()
            if "1956" in line or "established" in line_lc:
                live_facts.setdefault("established_1956", []).append(f"[{label}] {line[:200]}")
            if "ludhiana" in line_lc:
                live_facts.setdefault("ludhiana", []).append(f"[{label}] {line[:200]}")
            if "nba" in line_lc:
                live_facts.setdefault("nba", []).append(f"[{label}] {line[:200]}")
            if "naac" in line_lc:
                live_facts.setdefault("naac", []).append(f"[{label}] {line[:200]}")
            if "ikgptu" in line_lc or "punjab technical university" in line_lc:
                live_facts.setdefault("ikgptu", []).append(f"[{label}] {line[:200]}")
            if "autonom" in line_lc:
                live_facts.setdefault("autonomous", []).append(f"[{label}] {line[:200]}")
            if "tcs" in line_lc:
                live_facts.setdefault("tcs", []).append(f"[{label}] {line[:200]}")
            if "dispensary" in line_lc or "medical" in line_lc or "health" in line_lc:
                live_facts.setdefault("medical", []).append(f"[{label}] {line[:200]}")
            if "principal" in line_lc:
                live_facts.setdefault("principal", []).append(f"[{label}] {line[:200]}")
            if "1997" in line_lc and "cse" in line_lc:
                live_facts.setdefault("cse_1997", []).append(f"[{label}] {line[:200]}")
            if "mca" in line_lc and "2009" in line_lc:
                live_facts.setdefault("mca_2009", []).append(f"[{label}] {line[:200]}")
            if "mba" in line_lc and "2007" in line_lc:
                live_facts.setdefault("mba_2007", []).append(f"[{label}] {line[:200]}")

    print("=" * 70)
    print("LIVE SITE FACT VERIFICATION REPORT")
    print("=" * 70)

    # Report each fact
    report_facts = [
        ("GNDEC established in 1956", "established_1956"),
        ("GNDEC in Ludhiana, Punjab", "ludhiana"),
        ("NBA Accredited", "nba"),
        ("NAAC Accredited", "naac"),
        ("IKGPTU Affiliation", "ikgptu"),
        ("Autonomous College", "autonomous"),
        ("TCS Recruiter/Partner", "tcs"),
        ("Medical/Dispensary facilities", "medical"),
        ("Principal Name", "principal"),
        ("CSE established 1997", "cse_1997"),
        ("MCA started 2009", "mca_2009"),
        ("MBA started 2007-2008", "mba_2007"),
    ]

    for label, key in report_facts:
        snippets = live_facts.get(key, [])
        found = bool(snippets)
        print(f"\n{'✅ LIVE' if found else '❌ MISSING'}: {label}")
        if found:
            for s in snippets[:3]:
                print(f"   {s}")

    # Cross-check gold set
    print("\n" + "=" * 70)
    print("GOLD SET CORPUS vs LIVE SITE CROSS-CHECK")
    print("=" * 70)

    for item in gold:
        gt = item.get("ground_truth", {})
        facts = gt.get("key_facts", [])
        if not facts:
            continue
        # Find which facts are confirmed live
        confirmed = []
        missing = []
        for f in facts:
            f_lc = f.lower()
            found_live = any(f_lc in " ".join(res.get("lines", [])).lower()
                           for res in live.values())
            if found_live:
                confirmed.append(f)
            else:
                missing.append(f)

        if missing:
            print(f"\n⚠️  {item['id']}: {item['query'][:60]}")
            print(f"   ✅ Confirmed live: {confirmed}")
            print(f"   ❌ NOT on live site: {missing}")
            # Show corpus answer
            q_lc = item["query"].strip().lower()
            if q_lc in corpus:
                print(f"   CORPUS: {corpus[q_lc]['answer'][:200]}")
                print(f"   SOURCE: {corpus[q_lc]['source']}")

    # Department establishment years from live site
    print("\n" + "=" * 70)
    print("DEPARTMENT ESTABLISHMENT YEARS (LIVE)")
    print("=" * 70)
    depts = {
        "CSE": ("cse_1997", "1997", "Computer Science & Engineering"),
        "IT": ("it_2001", "2001", "Information Technology"),
        "ECE": ("ece_1981", "1981", "Electronics & Communication Engineering"),
        "EE": ("ee_1957", "1957", "Electrical Engineering"),
        "ME": ("me_1957", "1957", "Mechanical Engineering"),
        "MCA": ("mca_2009", "2009", "Computer Applications (MCA)"),
        "MBA": ("mba_2007", "2007", "Business Administration"),
    }
    for key, (fact_key, year, name) in depts.items():
        snippets = live_facts.get(fact_key, [])
        for s in snippets:
            print(f"  {name}: {s[:150]}")

    print("\n" + "=" * 70)
    print("CORPUS CORRECTIONS NEEDED")
    print("=" * 70)

    # Facts that are in corpus but NOT on live site
    corpus_only_facts = []
    for item in gold:
        gt = item.get("ground_truth", {})
        facts = gt.get("key_facts", [])
        q_lc = item["query"].strip().lower()
        for f in facts:
            f_lc = f.lower()
            found_live = any(f_lc in " ".join(res.get("lines", [])).lower()
                           for res in live.values())
            if not found_live and q_lc in corpus:
                corpus_only_facts.append({
                    "id": item["id"],
                    "query": item["query"],
                    "fact": f,
                    "corpus_answer": corpus[q_lc]["answer"][:300],
                    "corpus_source": corpus[q_lc]["source"],
                })

    for cf in corpus_only_facts[:20]:
        print(f"\n  ⚠️  {cf['id']}: '{cf['fact']}' NOT confirmed on live site")
        print(f"     Query: {cf['query'][:80]}")
        print(f"     Corpus says: {cf['corpus_answer'][:150]}")
        print(f"     Source: {cf['corpus_source']}")

    print(f"\nTotal unconfirmed facts: {len(corpus_only_facts)}")

    # Save the report
    report_path = os.path.join(DATA, "live_site_fact_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "live_facts": live_facts,
            "gold_crosscheck": [{"id": c["id"], "query": c["query"], "unconfirmed_fact": c["fact"],
                                 "corpus_answer": c["corpus_answer"], "source": c["corpus_source"]}
                                for c in corpus_only_facts],
        }, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved: {report_path}")

if __name__ == "__main__":
    main()
