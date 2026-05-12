import json, hashlib

def text_hash(t):
    return hashlib.md5(t.lower().strip().encode()).hexdigest()

data = json.load(open('data/gndec_data.json'))
print(f'Before: {len(data)}')

seen = set()
out = []
for p in data:
    q = (p.get('question') or '').strip()
    a = (p.get('answer') or '').strip()
    if len(q) < 10 or len(a) < 20:
        continue
    key = text_hash(q)
    if key in seen:
        continue
    seen.add(key)
    p['question'] = q
    p['answer'] = a
    out.append(p)

print(f'After dedup+filter: {len(out)}')
json.dump(out, open('data/gndec_data.json','w'), indent=2, ensure_ascii=False)
print('Saved.')
