"""Classify each fetched body by how it uses "mozGetAll"."""
import json, re, sys
d = sys.argv[1]
idx = json.load(open(f'{d}/index.json'))
out = []
for h, url, n, err in idx:
    if err:
        out.append({'body_hash': h, 'url': url, 'class': 'fetch-failed', 'error': err}); continue
    s = open(f'{d}/{h}.txt', encoding='utf8', errors='replace').read()
    if 'mozGetAll' not in s:
        out.append({'body_hash': h, 'url': url, 'class': 'changed-no-match'}); continue
    neighbors = re.search(r'mozFullScreenEnabled\W{1,8}mozGetAll\W{1,8}mozGetAllKeys\W{1,8}mozGetAsFile', s)
    terser = any(m in s for m in ('domprops', 'mangle_props', 'reserved_names', 'find_builtins', 'top_retain'))
    hits = [m.start() for m in re.finditer('mozGetAll', s)]
    list_hits = [i for i in hits if neighbors and abs(i - neighbors.start()) < 100]
    other = [i for i in hits if i not in list_hits]
    cls = ('domprops-list' + ('+terser' if terser else '')) if list_hits else ''
    if other:
        cls = (cls + '+' if cls else '') + 'code'
    out.append({'body_hash': h, 'url': url, 'class': cls, 'terser_markers': terser,
                'code_contexts': [s[max(0, i - 300):i + 300] for i in other[:4]]})
json.dump(out, open('data/classified.json', 'w'), indent=1)
import collections
print(collections.Counter(o['class'] for o in out))
