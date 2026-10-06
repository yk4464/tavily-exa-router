# Exa — Full Reference (snapshot 2026-08-18)

Docs: https://exa.ai/docs/reference/search (moved from docs.exa.ai)
Auth: `x-api-key: $EXA_API_KEY` (or `Authorization: Bearer`).
Base: `https://api.exa.ai`

## Contents

- /search — top-level parameters (+ deprecated/removed fields)
- contents options (text / highlights / summary / extras / subpages / maxAgeHours)
- Response fields that matter
- outputSchema example (verified)
- Recipes
- Pricing (2026-08)

## /search — top-level parameters

| Parameter | Values / default | Notes |
|---|---|---|
| `query` | required | natural language works well — the index is semantic |
| `type` | `auto` (default) / `instant` / `fast` / `deep-lite` / `deep` / `deep-reasoning` | old `neural`/`keyword` values are **deprecated**. Mode-by-mode latency, cost, and quality: `references/evidence.md` §2. `instant` was strong for official/paper lookup; `auto` is the broad default; `deep-lite` showed no stable quality gain |
| `numResults` | 1–100, default 10 | beyond 10 results bills $1/1k extra results |
| `includeDomains` / `excludeDomains` | arrays ≤1200 | supports wildcards (`*.substack.com`, verified strict) and path prefixes |
| `startPublishedDate` / `endPublishedDate` | ISO 8601 datetime | effective (verified all results inside window) |
| `category` | `news` / `company` / `publication` / `personal site` / `financial report` / `people` | dedicated `company`/`people` indices must not be combined with dates or `excludeDomains` — tested combinations returned 400; a single 200 for `company+excludeDomains` is drift, not a contract (`references/evidence.md` §3) |
| `additionalQueries` | 1–10 strings | documented for deep modes. A non-deep request was accepted but matched its control exactly — consistent with being ignored (`references/evidence.md` §3) |
| `systemPrompt` | string | natural-language source preferences, dedup rules, etc. |
| `outputSchema` | JSON schema | returns synthesized structured JSON in `output` (~+2s; verified working) |
| `stream` | bool | SSE, with `outputSchema` only |
| `moderation` | bool | filters unsafe content |
| `userLocation` | ISO country code | location hint |
| `contents` | object | see below |

Deprecated / removed: `startCrawlDate`/`endCrawlDate` are silently ignored;
`context` was replaced by `highlights` or `text`; the legacy `livecrawl`
selector was replaced by `maxAgeHours`; `/research` moved to `/search` with
`type: "deep-reasoning"`. `resolvedSearchType` is **not a stable contract**: the
2026-04/05 audit recorded it as removed, the current spec marks it deprecated
with "may be an empty string — do not branch on this value", and it was present
as `""` in every 2026-10-06 response. Treat it as absent and never branch on it.
`highlightScores` remains in the current response schema but was absent from all
observed results.

## `contents` options

On `/search`, content options are nested under `contents`; on standalone
`/contents`, they are top-level. Search pricing includes `text` and
`highlights` for the first 10 results. Standalone `/contents` bills $1/1k
pages **per requested content type**; `summary` is an additional charge.
Observed per-request costs: `references/evidence.md` §3.

| Option | Settings | Notes |
|---|---|---|
| `text` | `{maxCharacters: 1–10000, includeHtmlTags, verbosity: compact\|standard\|full, includeSections/excludeSections: header/navigation/banner/body/sidebar/footer/metadata}` | full text; direct indexed-page cases were usually around 0.5–1.2s, while forced live crawling could take about 30s |
| `highlights` | `{query, maxCharacters}` | LLM-picked snippets; verify presence because a standalone test returned an empty field while a combined request succeeded |
| `summary` | `{query, schema}` | focused or schema-shaped page summary; verify presence per result |
| `extras` | `{links, imageLinks, richLinks, richImageLinks, codeBlocks}` 0–1000 each | structured side-data |
| `subpages` | 0–100 + `subpageTarget` terms | crawl subpages of each result — returned empty in the 2026-08-18 test; do not depend on it |
| `maxAgeHours` | −1…720 | `-1` cache only, `0` force live, positive values accept cache up to that age. 721 was accepted once — outside the documented range, do not use |
| `livecrawlTimeout` | milliseconds | live-fetch timeout used with `maxAgeHours`; do not restore the deprecated `livecrawl` selector |

For standalone `/contents`, inspect `statuses[]` for each URL. The HTTP request
can succeed while individual pages report `error` tags such as
`CRAWL_TIMEOUT` or `SOURCE_NOT_AVAILABLE`.

## Response fields that matter

- `results[].publishedDate` — present on half of results in the broad run
  (80/160); the freshness signal Tavily lacks (`references/evidence.md` §1).
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

## Pricing (checked 2026-10-06)

Prices are per 1k requests and include **up to 10 results**. Billing follows what
the API actually returns, so `costDollars` is the authority when it matters.

- `instant`: **$4/1k**; `fast` and `auto`: $7/1k (measured 2026-10-06: `instant`
  returned `costDollars.total` 0.004 on three requests — earlier notes here said
  $7, which is stale).
- Each result **beyond 10 adds $1/1k**, charged linearly on the returned count:
  20 results → +0.010, 50 → 0.047, 100 requested returned 99 → 0.096.
- Search text and highlights are included for the first 10 results; beyond 10
  they are charged at $1/1k pages. `summary` is a separate $1/1k page charge.
- Standalone Contents: $1 / 1k pages **per requested type** (text + highlights
  on one page = 2). Verified 2026-10-06: one URL with text+highlights billed
  0.002, with `summary` 0.003.
- `outputSchema`: adds ~2s latency and **no separate charge** (measured
  2026-10-06, `costDollars` unchanged).
- Deep search: `deep-lite` and `deep` $12/1k; `deep-reasoning` $15/1k. All three
  re-verified 2026-10-06.
- Free tier: $20 signup credit + $10/month (vendor page has changed this
  figure more than once — check before quoting it).
