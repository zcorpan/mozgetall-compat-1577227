# `mozGetAll` compat research (bug 1577227)

Can Firefox remove `IDBObjectStore.mozGetAll`, `IDBIndex.mozGetAll` and `IDBIndex.mozGetAllKeys`?
See https://bugzilla.mozilla.org/show_bug.cgi?id=1577227#c10.

## Crawl data

`queries/01-mozgetall-bodies.sql`: HTTP Archive 2026-10-01 crawl, desktop client, root and secondary
pages, script and HTML responses whose body contains `mozGetAll` (78.7 TB processed). Output in
`queries/01-mozgetall-bodies.csv`: 957 responses, 110 distinct bodies, 948 pages (861 root pages).

`scripts/pages.py` classifies each page by its matches (`data/pages.jsonl`):

- 929 pages: name lists only. Terser's DOM property list (`domprops`, used to avoid mangling DOM
  names), javascript-obfuscator's reserved-names JSON, or the same list as a standalone chunk. 760
  of these are `*.webuntis.com` pages.
- 19 pages (10 sites): code. Either `if (store.mozGetAll) store.mozGetAll()… else
  store.openCursor()…` / `else store.getAll()` helpers, the zengm polyfill that only aliases
  `getAll = mozGetAll` when `getAll` is missing, or a check on an `IDBRequest` that is never true.
  `data/classified.json` has the code contexts from the live scripts (`scripts/fetch_bodies.py`,
  `scripts/classify.py`).

## Browser testing

Firefox built from mozilla-firefox/firefox 751f5671de2d plus a `dom.indexedDB.mozGetAll.enabled`
pref (`Pref=` on the three members in `IDBObjectStore.webidl` and `IDBIndex.webidl`), so "off"
removes them in windows and workers. `runs/smoke/` checks the pref and the detection on local test
pages, including a dedicated worker.

`scripts/harness.py` loads each page headless at 1376×768, waits 6 s, closes the tab and reads the
`dom.use_counters.dump.document` output from stderr (which also covers calls from dedicated
workers). In "on" mode a preload script logs main-thread lookups of the three members.

Detection (`runs/detect/on.jsonl`, all 948 pages, pref on; run with the same tree without the
pref patch): 6 pages call `IDBObjectStore.mozGetAll` during load, 0 call the `IDBIndex` members, and
no other page even looks them up. 1 page errored. The 6:

- rentacenter.com (2 pages): `sfchat/sf_data_send.js`, falls back to `openCursor()`.
- af.fineco.it (2 pages, login page): `drakeux.angular.js`, falls back to `openCursor()`.
- mevofit.com (2 pages): `cart_management_idb.js`, falls back to `openCursor()`.

Comparison (`runs/compare/`, the 19 code pages, pref build: A on, A2 on, B off;
`scripts/compare.py` → `runs/compare/comparison.json`): no new non-CSP errors in B, no errors
mentioning `mozGetAll`, same text length, element count and scroll size. The one screenshot
difference (rentacenter product page, a missing "Saved" link in B) didn't reproduce in 3 more runs
per mode (`runs/rentacenter/`, `review/`).

Browser run output (`runs/`) was scrubbed for publishing with `scripts/scrub_runs.py`: CSP reports
dropped, URL query strings and long payloads stripped, and final URLs, titles and the document URLs
in use counter lines removed.

## Limits

- Desktop crawl only, page load only: code behind login or interaction (famed, promtransinvest,
  siigo, lenzaos) wasn't reached, but all of it has a fallback.
- The crawl misses logged-in and intranet pages, which Firefox telemetry includes.
- Shared and service workers have no ancestor document, so their calls wouldn't show in the
  document counter.
