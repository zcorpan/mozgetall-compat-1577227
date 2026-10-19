"""Fetch one live copy of each distinct matching response body (by body_hash) for context review."""
import csv, collections, concurrent.futures, json, sys, urllib.request
out = sys.argv[1]
rows = list(csv.DictReader(open('queries/01-mozgetall-bodies.csv')))
by = collections.defaultdict(list)
for r in rows:
    by[r['body_hash']].append(r)
def fetch(item):
    h, rs = item
    url = rs[0]['url']
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:146.0) Gecko/20100101 Firefox/146.0'})
        data = urllib.request.urlopen(req, timeout=30).read()
        open(f'{out}/{h}.txt', 'wb').write(data)
        return h, url, len(data), None
    except Exception as e:
        return h, url, 0, str(e)
with concurrent.futures.ThreadPoolExecutor(16) as ex:
    res = list(ex.map(fetch, by.items()))
json.dump(res, open(f'{out}/index.json', 'w'), indent=1)
print(sum(1 for r in res if not r[3]), 'fetched,', sum(1 for r in res if r[3]), 'failed')
