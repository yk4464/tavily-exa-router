# Exa — Full Reference (snapshot 2026-08-18; sections re-checked 2026-10-06 / 2026-10-31 / 2026-11-18)

Docs: https://exa.ai/docs/reference/search (moved from docs.exa.ai)
Changelog: https://exa.ai/docs/changelog
Auth: `x-api-key: $EXA_API_KEY` (or `Authorization: Bearer`).
Base: `https://api.exa.ai`

## Contents

- /search — top-level parameters (+ deprecated/removed fields)
- contents options (text / highlights / summary / extras / subpages / maxAgeHours / snapshotAsOf)
- measured retrieval behaviour (per-site reach, cache settings)
- Response fields that matter
- outputSchema example (verified)
- Recipes
- Pricing (checked 2026-10-31)

## /search — top-level parameters

| Parameter | Values / default | Notes |
|---|---|---|
| `query` | required | natural language works well — the index is semantic |
| `type` | `auto` (API default) / `lite` (skill default) / `deep-lite` / `deep`; legacy `instant` / `fast` / `deep-reasoning` | Recommended types are `lite`, `auto`, and `deep`; the three legacy types keep working at their current prices. Exa's changelog maps `instant` → `lite` (while this skill keeps `instant` only for Chinese-language queries when dates matter); `fast` → `lite` (same search) or `auto` when the request needs a parameter `lite` does not support; `deep-reasoning` → `deep` (or Exa Agent). `lite` is $4/1k, cached content only, never a live fetch, with a restricted parameter set (below). Old `neural`/`keyword` values are **deprecated** but not inert — `neural` returned 200 at $0.004 and `keyword` at $0.007 with no warning on 2026-11-18. Mode-by-mode latency, cost, and quality: `references/evidence.md` §2, §7, §8. `lite` is the skill's default (including news, academic, and reviews per 2026-11-18 testing), `auto` is reserved for parameters `lite` rejects, `instant` is kept solely for Chinese date-sensitive queries, and `deep-lite` showed no stable quality gain. ([changelog](https://exa.ai/docs/changelog), [search ref](https://exa.ai/docs/reference/search), checked 2026-10-31, re-tested 2026-11-18) |
| `numResults` | 1–100, default 10 | beyond 10 results bills $1/1k extra results |
| `includeDomains` / `excludeDomains` | arrays ≤1200 | supports wildcards (`*.substack.com`, verified strict) and path prefixes |
| `startPublishedDate` / `endPublishedDate` | ISO 8601 datetime | effective for ordinary searches (verified all results inside window); rejected with the `company`/`people` categories ([search ref](https://exa.ai/docs/reference/search), checked 2026-10-31 (official docs, not measured)) |
| `category` | `company` / `publication` / `news` / `personal site` / `financial report` / `people`; other strings are accepted as category hints | `company` and `people` do **not** support `startPublishedDate`/`endPublishedDate`, and `people` also does **not** support `excludeDomains`; an unsupported filter returns 400. `company` + `excludeDomains` **is** supported by the spec — the single 200 in the 2026-08 audit was consistent with the contract, not drift. `publication` replaced the old `research paper` category; `pdf`/`github`/`tweet` are deprecated. ([search ref](https://exa.ai/docs/reference/search), [changelog](https://exa.ai/docs/changelog), checked 2026-10-31 (official docs, not measured); probes: `references/evidence.md` §3) |
| `additionalQueries` | 1–10 strings | only works with a deep-search type (official). A non-deep request was accepted but matched its control exactly — consistent with being ignored (`references/evidence.md` §3) |
| `systemPrompt` | string | natural-language source preferences, dedup rules, etc. |
| `outputSchema` | JSON schema, root `text` or `object` | returns synthesized output in `output.content`, with field-level citations/confidence in `output.grounding` (~+2s; verified working). Object schemas allow at most **10 properties in total** (nested and array-items properties count), at most **2 levels of nesting**, and every array must define `items`; exceeding a limit returns 400. Works with every search type **except `lite`**. ([search ref](https://exa.ai/docs/reference/search), [output schema limits](https://exa.ai/docs/search/deep-search#output-schema-limits), checked 2026-10-31 (official docs, not measured)) |
| `stream` | bool | SSE, with `outputSchema` only |
| `moderation` | bool | filters unsafe content |
| `userLocation` | ISO country code, or `{country, latitude, longitude}` | location hint; coordinates only affect place-dependent queries and do not set a country ([search ref](https://exa.ai/docs/reference/search), checked 2026-10-31 (official docs, not measured)) |
| `contents` | object | see below |

`lite` accepts only: `query` (a single string), `numResults`,
`contents.highlights`, `contents.text`, `contents.snapshotAsOf`, `category`
(including `company`/`people`), `includeDomains`, `excludeDomains`,
`startPublishedDate`, `endPublishedDate`, `userLocation`, `moderation`,
`objective`, `userIdentifier`, `metadata`, and `compliance`. Any other parameter
returns `400 INVALID_REQUEST_BODY` naming each unsupported field — including
`outputSchema`, `systemPrompt`, `stream`, `additionalQueries`,
`contents.summary`/`extras`/`subpages`/`subpageTarget`,
`contents.maxAgeHours`/`livecrawl`/`livecrawlTimeout` (any value, even `-1`),
and the deprecated `includeText`/`excludeText`/`startCrawlDate`/
`endCrawlDate`/`contents.context`. A parameter set to `null` counts as unset;
`false` and empty lists count as set. When `text` or `highlights` is requested,
results with no cached copy are left out of the response. Use `auto` when a
request needs an unsupported parameter. ([search
ref](https://exa.ai/docs/reference/search), [lite
guide](https://exa.ai/docs/search/quickstart#lite), checked 2026-10-31
(official docs, not measured))

**Measured 2026-10-31** (single local Windows egress; six queries each for
current events, academic, and Chinese; eight results): `lite` returned 8/8
results on every plain search call and billed `costDollars.total` 0.004.
Its result sets matched `fast` (mean Jaccard 0.988) and `auto` (0.988),
but only 0.199 with `instant`. Blind relevance/authority scores tied with `instant`, while `lite`
carried fewer publication dates (news 64.6%, academic 29.2%, Chinese 52.1%
versus `instant` 75.0/52.1/77.1%). Requesting `highlights` or `text` did not
reduce the count (8/8 on all 36 `lite` contents calls; all 288 results carried
content), but it changed the set (URL overlap with the plain response 0.914
for `highlights`, 0.697 for `text`; `instant` showed the same churn,
0.904/0.701, so this is a `/search` contents-request behavior, not a `lite`
cache penalty). `lite` + `outputSchema` and `lite` + `contents.summary`
both returned 400 naming the field. Details: `references/evidence.md` §7.

Deprecated / removed: `startCrawlDate`/`endCrawlDate` are ignored and now add
an `IGNORED_FIELD` warning to `warnings`; `includeText`/`excludeText` are
deprecated; `context` was replaced by `highlights` or `text`; the legacy
`livecrawl` selector was replaced by `maxAgeHours`; `/research` moved to
`/search` with `type: "deep-reasoning"` (itself now legacy).
`contents.extras.richLinks` and `contents.extras.codeBlocks` are deprecated;
`subpages`/`subpageTarget` on `/search` are deprecated in favor of `/contents`
(see below). `resolvedSearchType` is **not a stable contract**: the
2026-04/05 audit recorded it as removed, the current spec marks it deprecated
with "may be an empty string — do not branch on this value", and it was present
as `""` in every 2026-10-06 response. Treat it as absent and never branch on it.
`highlightScores` remains in the current response schema but was absent from all
observed results. The 2026-10-19 release adds `warnings` (ignored request
fields; log them, do not pass them to a model) and `notices` (how the results
were produced; pass them to the model) to `/search` responses.
([changelog](https://exa.ai/docs/changelog), [best
practices](https://exa.ai/docs/search/best-practices#warnings-and-notices),
checked 2026-10-31 (official docs, not measured))

## `contents` options

On `/search`, content options are nested under `contents`; on standalone
`/contents`, they are top-level. Search pricing includes `text` and
`highlights` for the first 10 results. Standalone `/contents` bills $1/1k
pages **per requested content type**; `summary` is an additional charge.
Observed per-request costs: `references/evidence.md` §3.

| Option | Settings | Notes |
|---|---|---|
| `text` | `{maxCharacters: 1–1,000,000, includeHtmlTags, verbosity: compact (default)\|standard\|full, includeSections/excludeSections: header/navigation/banner/body/sidebar/footer/metadata}` | full text; direct indexed-page cases were usually around 0.5–1.2s, while forced live crawling could take about 30s. `includeHtmlTags`, `verbosity`, and section filters apply to cached content; set `maxAgeHours: 0` to apply them to freshly fetched content ([search ref](https://exa.ai/docs/reference/search), checked 2026-10-31 (official docs, not measured)) |
| `highlights` | `{query, maxCharacters, verbosity?, dynamic?}`; `maxCharacters` 1–1,000,000 | LLM-picked snippets; verify presence because a standalone test returned an empty field while a combined request succeeded. `maxCharacters` is the preferred length control; `numSentences` (deprecated, mapped to ~1333 characters per sentence) and `highlightsPerUrl` (deprecated, ignored) remain accepted. `dynamic` and `verbosity` are a research-preview beta that requires the `Exa-Beta: dynamic-highlights-2026-08-28` header ([search ref](https://exa.ai/docs/reference/search), [changelog](https://exa.ai/docs/changelog), checked 2026-10-31 (official docs, not measured)) |
| `summary` | `{query, schema}` | focused or schema-shaped page summary; verify presence per result |
| `extras` | `{links, imageLinks, richImageLinks, richLinks (deprecated), codeBlocks (deprecated)}` 0–1000 each | structured side-data; `richLinks` and `codeBlocks` are deprecated ([search ref](https://exa.ai/docs/reference/search), checked 2026-10-31 (official docs, not measured)) |
| `subpages` | 0–100 + `subpageTarget` terms | **deprecated on `/search`**; use `/contents`, which still supports `subpages`/`subpageTarget`. The 2026-08-18 `/search` test returned empty — do not depend on it there ([search ref](https://exa.ai/docs/reference/search), [contents guide](https://exa.ai/docs/contents/quickstart#crawl-subpages), checked 2026-10-31 (official docs, not measured)) |
| `maxAgeHours` | −1…720 | `-1` cache only, `0` force live, positive values accept cache up to that age. 721 was accepted once — outside the documented range, do not use |
| `snapshotAsOf` | ISO 8601 date-time or `YYYY-MM-DD` | newest stored version of each page as of that instant; historical requests are served from stored versions and never fetch live. **Paid plans only**: returned `403 SNAPSHOT_NOT_ON_PLAN` on a free-tier account on 2026-11-18 (`references/evidence.md` §8.4) ([search ref](https://exa.ai/docs/reference/search), checked 2026-10-31) |
| `livecrawlTimeout` | 1–90,000 ms, default 10,000 | live-fetch timeout used with `maxAgeHours`; do not restore the deprecated `livecrawl` selector ([search ref](https://exa.ai/docs/reference/search), checked 2026-10-31 (official docs, not measured)) |

For standalone `/contents`, inspect `statuses[]` for each URL. The HTTP request
can succeed while individual pages report `error` tags such as
`CRAWL_TIMEOUT` or `SOURCE_NOT_AVAILABLE`.

### Measured retrieval behaviour (2026-08-18 to 2026-11-18)

Single-URL observations, not standing guarantees; the full 13-site matrix with
timings lives in `references/evidence.md` §4, §5.4, and §8.4.

- **2026-11-18 re-test:** Tieba is no longer cache-available (`maxAgeHours: -1`
  returned `CONTENT_NOT_CACHED`; `24` and `0` returned `CRAWL_HTTP_403`).
  Bilibili succeeded only with `maxAgeHours: 24` (`-1` returned
  `CONTENT_NOT_CACHED`, `0` returned HTTP 412). Linux.do succeeded across
  `-1`, `0`, and `24`. X and Reddit remained `SOURCE_NOT_AVAILABLE`, and Zhihu
  returned a login wall (`403` on forced live).
- Earlier runs (2026-08-18 to 2026-10-03) had reached Bilibili and Tieba via
  cache (`-1`/`24`), while forced live (`0`) was flaky and Tieba returned 500.
- Docs, GitHub, and Hacker News were the strongest targets overall.

## Response fields that matter

- `results[].publishedDate` — present on half of results in the broad run
  (80/160). It is returned without opt-in, unlike Tavily's `published_date`
  (`references/evidence.md` §1).
- `results[].score` — not returned by `auto`; do not rely on it as a portable
  ranking field across current search types.
- `costDollars` — per-request cost object (`{"total": 0.007, ...}`).
- `output` — synthesized result when `outputSchema` is used: generated value in
  `output.content`, field-level citations and confidence in `output.grounding`.
- `warnings` / `notices` — request problems (log them) and provenance notes
  (pass them to the model); each is omitted when empty, and both are open sets
  of `code`/`path`/`message` objects ([best
  practices](https://exa.ai/docs/search/best-practices#warnings-and-notices),
  checked 2026-10-31 (official docs, not measured)).

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
{"query": "<topic> announcements", "type": "lite",
 "startPublishedDate": "<ISO-8601 start of the user's window, never the current instant>", "numResults": 8}
```
(Rerun as `auto` if `highlights`/`text` come back thin.)

**Individual practitioner opinions:**
```json
{"query": "<product> real world experience criticism",
 "type": "lite", "category": "personal site", "numResults": 8}
```

**Company/entity research:**
```json
{"query": "<company name>", "type": "lite", "category": "company", "numResults": 5}
```
(no date filters with `company` — plan around it)

**Structured comparison table in one call:**
query + `outputSchema` (see above) — ideal for "list N options with X and Y"
tasks.

**Academic sweep:**
```json
{"query": "<topic> survey", "type": "lite", "numResults": 10}
```
(For citation tracing, do not lock `includeDomains` to `arxiv.org`.)

## Pricing (checked 2026-10-31)

https://exa.ai/docs/admin/pricing and https://exa.ai/docs/admin/billing — checked
2026-10-31 (official docs, not measured). Prices are per 1k requests and include
**up to 10 results**. Billing follows what the API actually returns, so
`costDollars` is the authority when it matters.

- `lite`: **$4/1k** (up to 10 results; AI page summaries are not offered on
  `lite`). Measured 2026-10-31: all 96 paid `lite` calls returned
  `costDollars.total` 0.004 (six-query × three-class run, including repeats
  and date probes); the two documented rejections billed nothing. Legacy
  `instant`: $4/1k — measured 2026-10-06: `instant` returned
  `costDollars.total` 0.004 on three requests (earlier notes here said $7, which
  is stale). `fast` and `auto`: $7/1k.
- Search pricing moved from $5 to $7/1k on 2026-03-03 (vendor changelog
  "Exa Pricing Update"); `lite` and legacy `instant` stayed at $4/1k. Treat any
  written price as provisional and read `costDollars` from the response.
- Each result **beyond 10 adds $1/1k**, charged linearly on the returned count:
  20 results → +0.010, 50 → 0.047, 100 requested returned 99 → 0.096.
- Search text and highlights are included for the first 10 results; beyond 10
  they are charged at $1/1k pages. `summary` is a separate $1/1k page charge and
  is not available on `lite`.
- Standalone Contents: $1 / 1k pages **per requested type** (text + highlights
  on one page = 2). Verified 2026-10-06: one URL with text+highlights billed
  0.002, with `summary` 0.003.
- `outputSchema`: adds ~2s latency and **no separate charge** (measured
  2026-10-06, `costDollars` unchanged).
- Deep search: `deep-lite` and `deep` $12/1k; `deep-reasoning` $15/1k (legacy).
  All three re-verified 2026-10-06. Documented latencies: ~4s for `deep-lite`,
  4–15s for `deep`, 12–40s for `deep-reasoning`.
- Free tier: **$10 in credits**, available in full on signup regardless of the
  date, then reset to $10 on the first day of every calendar month. It does
  **not** accumulate — unused free credits do not roll over, and only a user's
  first team receives the monthly grant. A one-time **$10 onboarding bonus** is
  added to that first team when the user completes dashboard onboarding and does
  not expire.
  (Earlier notes here said $20 signup + $10/month; the vendor page has changed
  this figure more than once — check before quoting it.)
- Rate limits on the same billing page: `/search` 10 QPS; `/search` with
  `deep-lite`/`deep`/`deep-reasoning` 5 QPS; `/contents` 100 QPS. Adding $1,000
  in credits within any 30-day window raises the team to 25 QPS for 90 days.
