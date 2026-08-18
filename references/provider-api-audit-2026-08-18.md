# Provider API Audit (2026-08-18)

This dated audit defines the parameter surface exercised by the repository's
comprehensive benchmark. It covers only one-off public-web search and known-URL
retrieval, the scope of this skill.

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
