#!/usr/bin/env python3
"""
GNDEC RAG 511-case benchmark harness.
Writes results to data/deep_rag_fact_accuracy_report.json.
"""
import sys, os, asyncio, time, json, numpy as np
import unicodedata, re, logging

sys.path.insert(0, '/app')
os.environ['PYTHONUNBUFFERED'] = '1'
logging.basicConfig(level=logging.ERROR)

from backend.agent import answer_sync
from backend.vectorstore import retrieve

def norm(text):
    if not text: return ''
    t = unicodedata.normalize('NFKC', str(text))
    t = t.replace('xa0', ' ').replace(' ', ' ')
    t = re.sub(r'\s+', ' ', t)
    return t.strip().lower()

def abstain(text):
    cues = ['only have knowledge','i do not have information','please contact',
            'no specific details','not offered at gndec','cannot provide',
            'do not possess']
    t = norm(text)
    return any(c in t for c in cues)

def score(res_text, rdocs, gt):
    kf = gt.get('key_facts', [])
    prob = gt.get('prohibited', [])
    must_tbl = gt.get('must_contain_tables', False)
    should_abstain = gt.get('should_abstain', False)

    ret_text = ' '.join([getattr(d,'page_content','') for d in rdocs]).lower()
    hits = [f for f in kf if norm(f) in ret_text]
    rh = len(hits)/len(kf)*100 if kf else 100.0

    t_lower = norm(res_text)
    matched = [f for f in kf if norm(f) in t_lower]
    ms = [f for f in kf if norm(f) not in t_lower]
    fs = len(matched)/len(kf)*100 if kf else 100.0

    halls = [p for p in prob if norm(p) in t_lower]
    hs = 0.0 if halls else 100.0

    has_tbl = ('|' in res_text and '---' in res_text) or ('| Sr No' in res_text)
    ts = 100.0 if (not must_tbl or has_tbl) else 0.0

    did_abstain = abstain(res_text)
    if should_abstain:
        asc = 100.0 if (did_abstain or len(matched) > 0) else 0.0
        passed = (hs == 100.0) and (asc == 100.0)
        ca = (hs * 0.5) + (asc * 0.5)
    else:
        asc = 100.0 if not did_abstain else (50.0 if fs > 50 else 0.0)
        passed = (fs >= 70.0) and (not halls) and (ts == 100.0)
        ca = (fs * 0.55) + (hs * 0.25) + (ts * 0.20)

    return {
        'passed': passed,
        'composite_accuracy': round(ca, 1),
        'fact_score': round(fs, 1),
        'retrieval_hit_rate': round(rh, 1),
        'matched_facts': matched,
        'missing_facts': ms,
        'hallucinations': halls,
        'has_table': has_tbl,
        'did_abstain': did_abstain,
    }

async def main():
    gold_file = '/app/data/gold_set_500.jsonl'
    items = [json.loads(l) for l in open(gold_file)]
    total = len(items)
    print(f'Loaded {total} gold test cases from {gold_file}')

    results, latencies, ret_lats = [], [], []
    cats = {}

    for idx, tc in enumerate(items, 1):
        sid = tc['id']
        cat = tc['category']
        query = tc['query']
        gt = tc['ground_truth']

        # Retrieval
        t0r = time.time()
        try:
            rdocs = retrieve(query, k=6)
        except Exception:
            rdocs = []
        ret_lat = round(time.time() - t0r, 3)
        ret_lats.append(ret_lat)

        # Generation
        t0 = time.time()
        try:
            session_id = 'eval_' + sid
            res = await answer_sync(query, 'eval_user', session_id)
            lat = round(time.time() - t0, 2)
            rtxt = res.get('answer', '')
            srcs = res.get('sources', [])
        except Exception as e:
            lat = round(time.time() - t0, 2)
            rtxt = 'ERROR: ' + str(e)
            srcs = []
        latencies.append(lat)

        sc = score(rtxt, rdocs, gt)

        cats.setdefault(cat, {'total': 0, 'passed': 0, 'accuracies': [], 'hits': [], 'lats': []})
        cats[cat]['total'] += 1
        if sc['passed']: cats[cat]['passed'] += 1
        cats[cat]['accuracies'].append(sc['composite_accuracy'])
        cats[cat]['hits'].append(sc['retrieval_hit_rate'])
        cats[cat]['lats'].append(lat)

        results.append({
            'id': sid, 'category': cat, 'query': query,
            'latency': lat, 'retrieval_latency': ret_lat,
            'num_sources': len(srcs),
            'score': sc,
            'response_preview': rtxt[:200].replace('\n', ' ')
        })

        sym = 'PASS' if sc['passed'] else 'FAIL'
        print(f'[{idx:03d}/{total}] {sid} ({cat}): {sym} Acc={sc["composite_accuracy"]}% '
              f'Hit={sc["retrieval_hit_rate"]}% Lat={lat}s (Ret:{ret_lat}s)')

        await asyncio.sleep(0.35)

    p50 = np.percentile(latencies, 50)
    p90 = np.percentile(latencies, 90)
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)

    print()
    print('=' * 85)
    print(f'{"Category":<28} | {"Passed":<7} | {"Rate":<9} | {"AvgAcc":<10} | {"Hit@K":<8} | {"AvgLat":<7}')
    print('-' * 85)
    total_p = sum(v['passed'] for v in cats.values())
    all_acc = [r['score']['composite_accuracy'] for r in results]
    all_hits = [r['score']['retrieval_hit_rate'] for r in results]

    for cat, s in sorted(cats.items()):
        pr = s['passed'] / s['total'] * 100
        avga = sum(s['accuracies']) / len(s['accuracies'])
        avgh = sum(s['hits']) / len(s['hits'])
        avgl = sum(s['lats']) / len(s['lats'])
        print(f'{cat:<28} | {s["passed"]}/{s["total"]:<5} | {pr:>7.1f}% | '
              f'{avga:>8.1f}% | {avgh:>6.1f}% | {avgl:>5.2f}s')

    ovr = total_p / total * 100
    print('-' * 85)
    print(f'{"OVERALL":<28} | {total_p}/{total:<5} | {ovr:>7.1f}% | '
          f'{sum(all_acc)/len(all_acc):>8.1f}% | {sum(all_hits)/len(all_hits):>6.1f}% | '
          f'{p50:>5.2f}s (p50)')
    print('=' * 85)
    print(f'Latency: p50={p50:.2f}s | p90={p90:.2f}s | p95={p95:.2f}s | p99={p99:.2f}s')

    report = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total_test_cases': total,
        'overall_pass_rate': round(ovr, 2),
        'overall_accuracy': round(sum(all_acc) / len(all_acc), 2),
        'overall_retrieval_hit_rate': round(sum(all_hits) / len(all_hits), 2),
        'latency_profile': {
            'p50': round(float(p50), 2),
            'p90': round(float(p90), 2),
            'p95': round(float(p95), 2),
            'p99': round(float(p99), 2),
        },
        'category_metrics': cats,
        'detailed_results': results,
    }
    with open('/app/data/deep_rag_fact_accuracy_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    print('\nReport saved to data/deep_rag_fact_accuracy_report.json')

if __name__ == '__main__':
    asyncio.run(main())
