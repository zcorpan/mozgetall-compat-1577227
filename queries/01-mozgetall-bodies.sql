-- Desktop script and HTML responses in the 2026-10-01 crawl whose body contains "mozGetAll".
SELECT
  client,
  is_root_page,
  rank,
  page,
  url,
  type,
  FARM_FINGERPRINT(response_body) AS body_hash,
  LENGTH(response_body) AS body_length,
  REGEXP_CONTAINS(response_body, r'mozGetAll[^K]') AS has_mozgetall,
  REGEXP_CONTAINS(response_body, r'mozGetAllKeys') AS has_mozgetallkeys,
  ARRAY_TO_STRING(ARRAY(
    SELECT DISTINCT s FROM UNNEST(REGEXP_EXTRACT_ALL(response_body, r'.{0,150}mozGetAll.{0,100}')) AS s LIMIT 5
  ), '\n---\n') AS snippets
FROM `httparchive.crawl.requests`
WHERE date = '2026-10-01'
  AND client = 'desktop'
  AND type IN ('script', 'html')
  AND response_body LIKE '%mozGetAll%'
