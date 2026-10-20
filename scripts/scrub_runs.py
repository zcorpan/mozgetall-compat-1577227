"""Scrub browser run output for publishing: drop CSP reports, strip URL query strings and
fragments, and drop long base64 payloads. Rewrites runs/**/*.jsonl and runs/**/*.json in place."""
import glob, json, re
URL_QUERY = re.compile(r'(https?://[^\s?#"\'<>]+)[?#][^\s"\'<>]*')
B64 = re.compile(r'[A-Za-z0-9+/_-]{100,}={0,2}')
def s(x):
    if isinstance(x, str):
        return B64.sub('[payload]', URL_QUERY.sub(r'\1', x))
    if isinstance(x, list):
        return [s(v) for v in x if not (isinstance(v, str) and 'Content-Security-Policy' in v)]
    if isinstance(x, dict):
        return {k: (v if k == 'page' else s(v)) for k, v in x.items()}
    return x
for f in glob.glob('runs/**/*.jsonl', recursive=True):
    lines = [json.dumps(s(json.loads(l))) for l in open(f) if l.strip()]
    open(f, 'w').write('\n'.join(lines) + '\n')
for f in glob.glob('runs/**/*.json', recursive=True):
    json.dump(s(json.load(open(f))), open(f, 'w'), indent=1)


# Then drop fields that reveal the tester's location via geo-redirects and localized content:
# (final URL, title, document URL in use counter lines).
def fix(r):
    r.pop('url', None); r.pop('title', None)
    if 'use_counters' in r:
        r['use_counters'] = sorted({u.split(' - ', 1)[0] for u in r['use_counters']})
    return r
for f in glob.glob('runs/**/*.jsonl', recursive=True):
    lines = [json.dumps(fix(json.loads(l))) for l in open(f) if l.strip()]
    open(f, 'w').write('\n'.join(lines) + '\n')
