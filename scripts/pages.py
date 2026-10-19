"""List each crawled page with the kind of mozGetAll match its responses have (list or code)."""
import csv, collections, json, re
rows = list(csv.DictReader(open('queries/01-mozgetall-bodies.csv')))
LIST = re.compile(r'mozFullScreenEnabled\W{1,8}mozGetAll\W{1,8}mozGetAllKeys|^\s*"mozGetAll",\s*\n---\n\s*"mozGetAllKeys",\s*$')
pages = collections.OrderedDict()
for r in sorted(rows, key=lambda r: (int(r['rank']), r['page'])):
    p = pages.setdefault(r['page'], {'page': r['page'], 'rank': int(r['rank']), 'is_root_page': r['is_root_page'] == 'true', 'kinds': set(), 'urls': []})
    p['kinds'].add('list' if LIST.search(r['snippets']) else 'code')
    p['urls'].append(r['url'])
with open('data/pages.jsonl', 'w') as f:
    for p in pages.values():
        p['kind'] = 'code' if 'code' in p['kinds'] else 'list'
        del p['kinds']
        f.write(json.dumps(p) + '\n')
print(collections.Counter(p['kind'] for p in pages.values()))
