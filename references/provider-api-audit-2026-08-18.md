# Provider API Audit (2026-08-18)

This dated audit defines the parameter surface exercised by the repository's
comprehensive benchmark. It covers only one-off public-web search and known-URL
retrieval, the scope of this skill.

**Superseded / corrected (dated).** The body below preserves the 2026-08-18
audit as written. Later checks changed these points; the newer source wins:

- **Search pricing `$7/1k`.** It now applies to `auto` and `fast`; `instant`
  is `$4/1k`, as is the `lite` type added on 2026-10-19. A 2026-10-06 live
  check billed `instant` at 0.004 per request (`references/evidence.md` §6;
  `references/exa.md`).
- **"Explicit parameters override `auto_parameters`."** Not observed: explicit
  `search_depth: basic` still billed 2 credits and returned the same ordered
  results as basic on 2026-08-18 and 2026-10-03 (`references/evidence.md` §3,
  §5.3). The sentence records vendor intent, not measured behavior.
- **`resolvedSearchType` / `highlightScores` "removed".** The current schema
  still documents `highlightScores` (absent from observed responses), and
  `resolvedSearchType` appeared in 2026-10-03 responses and as `""` in
  2026-10-06 responses; the spec marks `resolvedSearchType` deprecated, not
  removed (`references/exa.md`).
- **`company` and `people` vs `excludeDomains`.** The current reference
  forbids `startPublishedDate`/`endPublishedDate` for both categories and
  `excludeDomains` only for `people`; `company+excludeDomains` is allowed
  (only the listed restrictions are rejected) and returned 200 on 2026-08-18,
  2026-10-03, and 2026-10-06 (`references/evidence.md` §3, §5.3).
- **Search-type list.** Since the 2026-10-19 Exa changelog, `lite`, `auto`,
  and `deep` are the recommended types; `instant`, `fast`, and
  `deep-reasoning` are legacy but still served
  (https://exa.ai/docs/changelog).

## Tavily

- Search accepts queries under 1,500 characters and depths `ultra-fast`,
  `fast`, `basic`, and `advanced`. Explicit parameters override
  `auto_parameters`; automatic tuning may upgrade a request to `advanced`.
- Date controls are `time_range` or exact `start_date`/`end_date`; published
  dates are expected primarily for the `news` topic.
- Extract accepts up to 20 URLs plus optional `query`, `chunks_per_source`
  (1–5), `extract_depth`, media flags, `format`, `timeout` (1–60), and
  `include_usage`.
- Basic/advanced search costs 1/2 credits. Basic/advanced extraction costs
  1/2 credits per five successful URLs; failed extractions are not billed.

Sources:

- https://docs.tavily.com/documentation/api-reference/endpoint/search
- https://docs.tavily.com/documentation/best-practices/best-practices-search
- https://docs.tavily.com/documentation/api-reference/endpoint/extract
- https://docs.tavily.com/documentation/api-credits

## Exa

- Search types are `instant`, `fast`, `auto`, `deep-lite`, `deep`, and
  `deep-reasoning`; `numResults` is 1–100. `additionalQueries` is restricted
  to deep modes and accepts 1–10 entries.
- `company` and `people` cannot be combined with published-date filters or
  `excludeDomains`.
- Deprecated or removed surfaces include crawl-date filters, `context`, the
  legacy `livecrawl` selector, `/research`, `resolvedSearchType`, and
  `highlightScores`.
- `/search` nests retrieval options under `contents`; `/contents` uses the same
  options at top level. Live retrieval uses `maxAgeHours: 0` and optionally
  `livecrawlTimeout`; callers must inspect per-URL `statuses[]`.
- Search costs $7/1k requests for up to 10 results, with additional result and
  summary charges. Standalone Contents costs $1/1k pages per content type.
  Deep-lite/deep cost $12/1k; deep-reasoning costs $15/1k.

Sources:

- https://docs.exa.ai/docs/reference/search
- https://docs.exa.ai/docs/reference/contents-retrieval
- https://docs.exa.ai/docs/reference/pricing
- https://docs.exa.ai/docs/reference/rate-limits
- https://docs.exa.ai/docs/changelog

## Evidence Boundary

Documentation defines accepted fields and intended semantics. Live benchmark
results in `references/evidence.md` determine whether a parameter currently
works, how fast it is from the test machine, and whether its output is useful.

The 2026-08-18 endpoint accepted several values outside or against the stated
contract: a 1,501-character Tavily query, `max_results: 21`, Tavily Extract
`timeout: 61`, Exa `maxAgeHours: 721`, non-deep `additionalQueries`, and
`company+excludeDomains`. It also charged 2 Tavily credits even when
`auto_parameters` was paired with explicit `search_depth: basic`. These are
recorded as drift observations, not as supported features; portable callers
should retain the documented limits and combinations.

Re-checked 2026-10-31: `company+excludeDomains` is not prohibited by the
current reference and is no longer treated as drift; the other items above
remain drift observations. See the re-check below.

## Official docs re-check 2026-10-31

Documentation review only — no API calls. Each item was checked against the
vendor page cited; these are page statements, not measurements.

### Exa

- **Search types and pricing (changelog 2026-10-19):** `lite`, `auto`, and
  `deep` are the recommended types; `instant`, `fast`, and `deep-reasoning`
  are legacy and keep current prices. `lite` costs USD 4/1k, serves cached
  content only (never fetches live), and rejects an unsupported parameter with
  HTTP 400 naming it. Pricing page: `lite` and `instant` USD 4/1k;
  `auto`/`fast` USD 7/1k; `deep-lite`/`deep` USD 12/1k; `deep-reasoning`
  USD 15/1k. Sources: https://exa.ai/docs/changelog and
  https://exa.ai/docs/admin/pricing
- **Category restrictions:** `company` and `people` do not support
  `startPublishedDate`/`endPublishedDate`; `people` also does not support
  `excludeDomains`; unsupported combinations return 400. Source:
  https://exa.ai/docs/reference/search
- **`outputSchema`:** object schemas are capped at 10 properties in total
  (nested and array-item properties count), 2 levels of nesting, and every
  array must define `items`. Synthesis adds about 2 seconds. Same source.
- **`contents.text` / `contents.highlights`:** `maxCharacters` accepts
  1–1,000,000. Same source.
- **Deprecated contents fields:** `richLinks` and `codeBlocks` are marked
  deprecated. On `/search`, `subpages` and `subpageTarget` are deprecated;
  send result URLs to `/contents` with those fields instead. Same source.
- **Free tier:** USD 10 in credits every month, non-accumulating and reset
  on the first of the month, plus a one-time USD 10 onboarding bonus. Source:
  https://exa.ai/docs/admin/billing

### Tavily

- **Published-date controls:** `include_published_date` (default `false`,
  beta, automatically enabled for `topic: news`) adds `published_date`;
  results with no detectable date return `null`. `filter_by_published_date`
  removes results outside the requested window and undated results; setting
  it true also enables `include_published_date`. Source:
  https://docs.tavily.com/documentation/api-reference/endpoint/search
- **Freshness:** `max_age_hours` accepts `1`–`720`, `0` (always live), or
  `-1` (never live). On non-paying plans live fetching is best-effort and a
  request may be refused with `434 Flex tier capacity exceeded` (changelog
  October 2026).
- **Domain mode:** `include_domains_mode` is `restrict` (default) or
  `prefer`; setting it without `include_domains` returns 400 (changelog
  August 2026).
- **Language:** `language` boosts a language; `filter_by_language: true`
  makes it a strict filter and requires `language` (else 400) (changelog
  August 2026).
- **Time range:** `time_range` also accepts the aliases `d`/`w`/`m`/`y`.
- **Chunking:** `basic` now returns reranked chunks, and
  `chunks_per_source` (default 3, range 1–3) applies to `basic`, `fast`, and
  `advanced` (changelog July 2026). The endpoint reference describes about
  500 characters per chunk for `basic`/`fast` and 800 for `advanced`; the
  Extract reference describes about 800 characters, while the changelog
  still says up to 500. Sources:
  https://docs.tavily.com/documentation/api-reference/endpoint/search,
  https://docs.tavily.com/documentation/api-reference/endpoint/extract, and
  https://docs.tavily.com/changelog
