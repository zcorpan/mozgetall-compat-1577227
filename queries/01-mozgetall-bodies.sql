-- Responses (scripts and HTML) in the 2026-10-01 crawl whose body contains "mozGetAll".
SELECT
  client,
  is_root_page,
  rank,
  page,
  url,
  type,
  REGEXP_CONTAINS(response_body, r'mozGetAll[^K]') AS has_mozgetall,
  REGEXP_CONTAINS(response_body, r'mozGetAllKeys') AS has_mozgetallkeys,
  ARRAY_TO_STRING(ARRAY(
    SELECT DISTINCT s FROM UNNEST(REGEXP_EXTRACT_ALL(response_body, r'.{0,100}mozGetAll.{0,60}')) AS s LIMIT 5
  ), '\n---\n') AS snippets
FROM `httparchive.crawl.requests`
WHERE date = '2026-10-01'
  AND type IN ('script', 'html')
  AND response_body LIKE '%mozGetAll%'
