# Exa — Full Reference (as of 2026-08)

Docs: https://exa.ai/docs/reference/search (moved from docs.exa.ai)
Auth: `x-api-key: $EXA_API_KEY` (or `Authorization: Bearer`).
Base: `https://api.exa.ai`

## /search — top-level parameters

| Parameter | Values / default | Notes |
|---|---|---|
| `query` | required | natural language works well — the index is semantic |
| `type` | `auto` (default) / `instant` / `fast` / `deep-lite` / `deep` / `deep-reasoning` | old `neural`/`keyword` values are **deprecated**. Measured: `auto` best default; `instant` noisier with no reliable latency advantage; `deep-lite` 1.7x cost, 4–8x latency, no clear quality gain. Vendor ballparks (not SLAs): `deep-lite` ~4s, `deep` 4–15s, `deep-reasoning` 12–40s; our single `deep` run: 5.1s, $0.012, n=1 |
| `numResults` | 1–100, default 10 | beyond 10 results bills $1/1k extra results |
| `includeDomains` / `excludeDomains` | arrays ≤1200 | supports wildcards (`*.substack.com`, verified strict) and path prefixes |
| `startPublishedDate` / `endPublishedDate` | ISO 8601 datetime | effective (verified all results inside window) |
| `category` | `news` / `company` / `publication` / `personal site` / `financial report` / `people` | `company`/`people` use dedicated indices: **no date filters, no excludeDomains — combining returns HTTP 400** (verified) |
| `additionalQueries` | 1–10 strings | query variants, deep modes only |
| `systemPrompt` | string | natural-language source preferences, dedup rules, etc. |
| `outputSchema` | JSON schema | returns synthesized structured JSON in `output` (~+2s; verified working) |
| `stream` | bool | SSE, with `outputSchema` only |
| `moderation` | bool | filters unsafe content |
| `userLocation` | ISO country code | location hint |
| `contents` | object | see below |

Deprecated / no-op: `startCrawlDate`/`endCrawlDate`, `context`, `livecrawl`
(replaced by `contents.maxAgeHours`).

## `contents` options (billed $1/1k pages **per content type**)

| Option | Settings | Notes |
|---|---|---|
| `text` | `{maxCharacters: 1–10000, includeHtmlTags, verbosity: compact\|standard\|full, includeSections/excludeSections: header/navigation/banner/body/sidebar/footer/metadata}` | full text; near-zero added latency (parallel pipeline, measured ~690ms total) |
| `highlights` | `{query, maxCharacters}` | LLM-picked relevant snippets (verified good) |
| `summary` | `{query, schema}` | LLM page summary, can target a focus question (verified) |
| `extras` | `{links, imageLinks, richLinks, richImageLinks, codeBlocks}` 0–1000 each | structured side-data |
| `subpages` | 0–100 + `subpageTarget` terms | crawl subpages of each result — **returned empty in testing; do not depend on it** |
| `maxAgeHours` | −1…720 | cache freshness; `0` = force fresh fetch. Note: forced-live failed on all 5 anti-bot/JS-heavy community test sites — cached/indexed retrieval is its stronger path; Tavily `/extract` proved more reliable on hostile targets |

## Response fields that matter

- `results[].publishedDate` — present on ~half of results (83/159 in testing);
  the freshness signal Tavily lacks.
- `results[].score` — **not returned**; no built-in relevance ranking signal.
- `costDollars` — per-request cost object (`{"total": 0.007, ...}`).
- `output` — synthesized JSON when `outputSchema` is used.

## outputSchema example (verified)

```json
{
  "query": "best vector databases 2026",
  "numResults": 10,
  "type": "auto",
  "outputSchema": {
    "type": "object",
    "properties": {
      "databases": {
        "type": "array",
        "items": {"type": "object", "properties": {
          "name": {"type": "string"},
          "url": {"type": "string"},
          "best_for": {"type": "string"}}}}}}
}
```
Returns `{"databases": [{"name": "Pinecone", "url": "...", "best_for": "..."}]}`.

## Recipes

**Recent events with dates:**
```json
{"query": "<topic> announcements", "type": "auto",
 "startPublishedDate": "<ISO-8601 timestamp computed at request time>", "numResults": 8}
```

**Individual practitioner opinions:**
```json
{"query": "<product> real world experience criticism",
 "category": "personal site", "numResults": 8}
```

**Company/entity research:**
```json
{"query": "<company name>", "category": "company", "numResults": 5}
```
(no date filters with `company` — plan around it)

**Structured comparison table in one call:**
query + `outputSchema` (see above) — ideal for "list N options with X and Y"
tasks.

**Academic sweep:**
```json
{"query": "<topic> survey", "includeDomains": ["arxiv.org"], "numResults": 10}
```

## Pricing (2026-08)

- Search: $7 / 1k requests (≤10 results each); extra results $1/1k.
- Contents: $1 / 1k pages **per type** (text + highlights on one page = 2).
- Summaries: $1/1k pages.
- Deep search: `deep-lite` and `deep` $12/1k; `deep-reasoning` $15/1k.
- Free tier: $20 signup credit + $10/month.
