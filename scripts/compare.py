"""Compare A, A2 (pref on) and B (pref off) runs: non-CSP errors new in B, and screenshot pixel differences."""
import json, re, sys
from PIL import Image, ImageChops
d = sys.argv[1]
def load(n): return {r['page']: r for r in map(json.loads, open(f'{d}/{n}.jsonl'))}
a, a2, b = load('a'), load('a2'), load('b')
def norm(e): return re.sub(r'https?://\S+', 'URL', re.sub(r'\d+', 'N', e))
def errs(r): return {norm(e) for e in r.get('errors', []) if 'Content-Security-Policy' not in e}
def diff(x, y):
    try:
        i, j = Image.open(f"{d}/screenshots/{x}"), Image.open(f"{d}/screenshots/{y}")
    except Exception:
        return None
    if i.size != j.size: return 'size'
    bbox = ImageChops.difference(i.convert('RGB'), j.convert('RGB')).getbbox()
    return 0 if not bbox else (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
out = []
for p in a:
    x, y, z = a[p], a2.get(p, {}), b.get(p, {})
    rec = {'page': p, 'called_in_A': bool(x.get('use_counters')), 'called_in_B': bool(z.get('use_counters')),
           'new_errors_in_B': sorted(errs(z) - errs(x) - errs(y)),
           'mozgetall_errors_in_B': [e for e in z.get('errors', []) if 'mozGetAll' in e],
           'pixels_A_A2': diff(f"a/{x.get('screenshot')}", f"a2/{y.get('screenshot')}"),
           'pixels_A_B': diff(f"a/{x.get('screenshot')}", f"b/{z.get('screenshot')}")}
    out.append(rec)
    print(json.dumps(rec))
json.dump(out, open(f'{d}/comparison.json', 'w'), indent=1)
