# Exa — Full Reference (as of 2026-08)

Docs: https://exa.ai/docs/reference/search (moved from docs.exa.ai)
Auth: `x-api-key: $EXA_API_KEY` (or `Authorization: Bearer`).
Base: `https://api.exa.ai`

## /search — top-level parameters

| Parameter | Values / default | Notes |
|---|---|---|
| `query` | required | natural language works well — the index is semantic |
| `type` | `auto` (default) / `instant` / `fast` / `deep-lite` / `deep` / `deep-reasoning` | old `neural`/`keyword` values are **deprecated**. Latest four-query medians: instant 0.97s, fast 1.15s, auto 1.78s, deep-lite 5.99s, deep 5.26s, deep-reasoning 12.68s. `instant` was strong for official/paper lookup; `auto` is the broad default; `deep-lite` showed no stable quality gain |
| `numResults` | 1–100, default 10 | beyond 10 results bills $1/1k extra results |
| `includeDomains` / `excludeDomains` | arrays ≤1200 | supports wildcards (`*.substack.com`, verified strict) and path prefixes |
| `startPublishedDate` / `endPublishedDate` | ISO 8601 datetime | effective (verified all results inside window) |
| `category` | `news` / `company` / `publication` / `personal site` / `financial report` / `people` | dedicated `company`/`people` indices should not be combined with dates or `excludeDomains`. Three tested combinations returned 400; `company+excludeDomains` returned 200 once, but is not a stable contract |
| `additionalQueries` | 1–10 strings | documented for deep modes. A non-deep request returned 200 but matched its control exactly, consistent with being ignored |
| `systemPrompt` | string | natural-language source preferences, dedup rules, etc. |
| `outputSchema` | JSON schema | returns synthesized structured JSON in `output` (~+2s; verified working) |
| `stream` | bool | SSE, with `outputSchema` only |
| `moderation` | bool | filters unsafe content |
| `userLocation` | ISO country code | location hint |
| `contents` | object | see below |

Deprecated / removed: `startCrawlDate`/`endCrawlDate` are silently ignored;
`context` was replaced by `highlights` or `text`; the legacy `livecrawl`
selector was replaced by `maxAgeHours`; `/research` moved to `/search` with
`type: "deep-reasoning"`; `resolvedSearchType` and `highlightScores` were
removed from responses in 2026-04/05.

## `contents` options

On `/search`, content options are nested under `contents`; on standalone
`/contents`, they are top-level. Search pricing includes `text` and
`highlights` for the first 10 results. Standalone `/contents` bills $1/1k
pages **per requested content type**; `summary` is an additional charge.

| Option | Settings | Notes |
|---|---|---|
| `text` | `{maxCharacters: 1–10000, includeHtmlTags, verbosity: compact\|standard\|full, includeSections/excludeSections: header/navigation/banner/body/sidebar/footer/metadata}` | full text; direct indexed-page cases were usually around 0.5–1.2s, while forced live crawling could take about 30s |
| `highlights` | `{query, maxCharacters}` | LLM-picked snippets; verify presence because a standalone test returned an empty field while a combined request succeeded |
| `summary` | `{query, schema}` | focused or schema-shaped page summary; verify presence per result |
| `extras` | `{links, imageLinks, richLinks, richImageLinks, codeBlocks}` 0–1000 each | structured side-data |
| `subpages` | 0–100 + `subpageTarget` terms | crawl subpages of each result — **returned empty in testing; do not depend on it** |
| `maxAgeHours` | −1…720 | `-1` cache only, `0` force live, positive values accept cache up to that age. 721 was accepted once but is outside the documented range |
| `livecrawlTimeout` | milliseconds | live-fetch timeout used with `maxAgeHours`; do not restore the deprecated `livecrawl` selector |

For standalone `/contents`, inspect `statuses[]` for each URL. The HTTP request
can succeed while individual pages report `error` tags such as
`CRAWL_TIMEOUT` or `SOURCE_NOT_AVAILABLE`.

## Response fields that matter

- `results[].publishedDate` — present on half of results (80/160 in the broad run);
  the freshness signal Tavily lacks.
- `results[].score` — not returned by `auto`; do not rely on it as a portable
  ranking field across current search types.
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
- Search: text and highlights are included for the first 10 results; summaries
  and results beyond 10 add charges.
- Standalone Contents: $1 / 1k pages **per requested type** (text + highlights
  on one page = 2).
- Summaries: $1/1k pages.
- Deep search: `deep-lite` and `deep` $12/1k; `deep-reasoning` $15/1k.
- Free tier: $20 signup credit + $10/month.
