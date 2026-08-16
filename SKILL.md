---
name: tavily-exa-router
description: >
  Choose and configure the right web search API between Tavily and Exa for any
  query. Use when a web search is needed and Tavily or Exa (API, CLI, or MCP
  tool) is available — routing works best with both, and each service's mode,
  parameter, and pricing guidance applies on its own. Also use when deciding
  which service fits a query type (news, academic papers, community opinions,
  product reviews, entity or company research, Chinese content); when picking
  search modes, depths, or parameters for either service; when fetching a
  known URL via Tavily Extract; when one service's results look weak and a
  second opinion could help; or when optimizing search cost, latency, or
  result structure.
license: MIT
metadata:
  version: "1.0"
  evidence-tested: "2026-08"
---

# Tavily vs Exa Search Router

Two complementary search APIs. Measured per-query result overlap (domain
Jaccard) averages just 0.22, so they cover different corners of the web —
routing well matters more than either service's raw quality. Every rule below
is backed by the tests in `references/evidence.md` or multi-source community
reports (`references/community-feedback.md`) — re-verify if you use this
after mid-2027.

**One-line roles:**

- **Tavily** — fast scored search that reaches forum/community content (Reddit,
  HN, Quora), returns an LLM answer on demand, and is the only one of the two
  with a URL-fetch endpoint (`/extract`).
- **Exa** — semantic search with published dates on ~half of results, strong on
  primary/official sources, academic pages, and non-English content, plus
  structured JSON output and LLM snippets built in.

## Scope and pre-flight

This skill routes **one-off public-web retrieval** between Tavily and Exa. It
does not: judge URL safety (extracting a page proves nothing about its safety
— don't fetch an untrusted URL just to verdict it), access private or
login-gated sources, create monitors or recurring alerts, serve live
quotes/inventory/retail prices, or guarantee exhaustive result lists. For
monitoring, use a dedicated product (e.g. Exa Monitors); for completeness,
say so and accept the limits.

Before routing, check: is the source public? Is this a one-off search or an
ongoing task? Is real-time data actually required, or just recent pages?
Does the requested count exceed provider limits (Tavily 20, Exa 100)?

When two routing rows match, the more specific row wins — e.g. a
Chinese-language forum request is a **forum** request first (route to
Tavily) before it is a general Chinese-content request. Never combine Exa
`company`/`people` categories with date filters or `excludeDomains`.

## The 10-second routing table

| Task | Use | Recipe |
|---|---|---|
| Current events / what's new | Exa | `type: auto`, add `startPublishedDate` for recency; Tavily `topic: news` + `time_range` is a shallower but simpler alternative |
| Financial markets coverage | Tavily | `topic: "finance"` vertical. Neither service is a live quote/inventory/price database — for "right now" prices, say so |
| Academic / papers / surveys | Exa | `type: auto`. Unfiltered spot check: 7/8 arXiv results vs Tavily's 2/8 authoritative hits. Caveat: semantic search ≠ citation tracing — for "papers citing X" don't lock `includeDomains` to arxiv.org; scholarly indexes and repos carry most citations |
| Community opinions, forum threads (any language) | Tavily | default search; surfaces Reddit/HN/Quora reliably (2.6x more community domains than Exa). This row wins over the language row for forums |
| Deep individual experience posts (blogs) | Exa | `category: "personal site"` — 8/8 on-topic opinion pieces in our spot check (evidence.md §1.1) |
| Chinese-language content (general) | Exa | useful first attempt: returned dated, specific pages in spot checks while Tavily returned undated roundups (evidence.md §1). Community reports are mixed on accuracy — cross-check when it matters; for Chinese forums use the community row above |
| Direct answer needed (no reading) | Tavily | `include_answer: "basic"` (or `"advanced"` for a longer synthesis) |
| Fetch a known URL's content | Tavily | `/extract` endpoint — the only fetcher of the two (see "Fetching pages") |
| Structured data extraction (lists, comparisons) | Exa | `outputSchema` returns clean JSON (~+2s latency) |
| Entity / company / people research | Exa | `category: "company"` or `"people"` — never combine with date filters or `excludeDomains` (HTTP 400). If freshness also matters, use a general/news search instead |
| Product reviews with dates | Exa | default; date metadata makes freshness checkable (Tavily results carry no dates) |
| Tight agent loop, auto-filter results | Tavily | every result has a relevance `score` — a starting heuristic, not a correctness signal; under ~0.3 is usually filler |
| Broad one-off research, coverage over cost | Exa | `type: auto` + larger `numResults` (up to 100). `deep-lite` only for a deliberate wide-net pass — slower and costlier without a clear quality gain. No finite result set is exhaustive |

If both are equally plausible for the task, prefer **Exa** for read-heavy
research and **Tavily** for interactive speed. When one service's results look
weak, run the other — with 22% overlap the second call usually adds new
sources rather than duplicating.

## Mode selection (measured, 2026-08)

**Tavily `search_depth`:**
- `basic` — default, 1 credit. Correct choice almost always.
- `advanced` — 2 credits, ~1-2s slower. Real but modest quality gain, best on
  factual and Chinese queries. Use when quality matters more than cost.
- `fast` / `ultra-fast` — **avoid**. Measured: duplicate results (same page
  4x), spam/gambling sites on factual queries, weaker Chinese results — and no
  actual speed gain over `basic`.

**Exa `type`:**
- `auto` — default and best balance. Surfaced official docs (OpenAI, OWASP)
  first in tests.
- `instant` — slightly noisier, and in our runs it showed no reliable
  wall-clock advantage over `auto`; use only when you deliberately want the
  shallow mode.
- `fast` — no measured benefit over `auto`. Skip.
- `deep-lite` — 1.7x cost ($0.012 vs $0.007), 4-8x latency in our runs
  (vendor ballpark ~4s), and no clear quality gain in tests. Reserve for
  "cast a wide net" passes; not a default. Vendor guidance (not an SLA):
  `deep` ≈4-15s, `deep-reasoning` ≈12-40s; our single `deep` run took 5.1s
  at $0.012. Reserve both for research workflows, not ordinary lookups.

**Content extraction is not equal:** with full text enabled, Exa stayed at
~690ms (parallel pipeline) while Tavily rose to ~1300ms. When you need page
text alongside results, Exa is effectively 2x faster.

All latency figures above are directional single-machine, single-window
measurements — not SLAs. Expect variation by region, load, and query.

## Parameter quick reference

If you're calling a Tavily/Exa CLI or MCP tool instead of the HTTP API, map
the JSON fields below to the tool's arguments one-to-one.

**Tavily `/search`** (full table: `references/tavily.md`):

```json
POST https://api.tavily.com/search
{"query": "...", "max_results": 8, "search_depth": "basic",
 "topic": "news", "time_range": "week",
 "include_answer": "advanced", "include_raw_content": "markdown",
 "include_domains": ["..."], "exclude_domains": ["..."]}
```
Allowed values — `topic`: `general`/`news`/`finance`; `time_range`:
`day`/`week`/`month`/`year`; `include_answer`: `basic`/`advanced`. Pick one
per call; never copy pipe lists into a real request.
Auth: `Authorization: Bearer $TAVILY_API_KEY`. Every result includes a
relevance `score` (use it to filter, e.g. drop < 0.3).

**Exa `/search`** (full table: `references/exa.md`):

```json
POST https://api.exa.ai/search
{"query": "...", "numResults": 8, "type": "auto",
 "startPublishedDate": "<ISO-8601 timestamp computed at request time>",
 "category": "news",
 "includeDomains": ["*.example.com"],
 "contents": {"highlights": {"query": "..."}}}
```
Compute `startPublishedDate` from the user's freshness window — never copy a
hard-coded date. `category`: `news`/`company`/`publication`/`personal site`/
`financial report`/`people`. Adding `text` alongside `highlights` doubles
contents billing — request full text only when needed.
Auth: `x-api-key: $EXA_API_KEY`. Results often carry `publishedDate`; response
carries `costDollars`.

Parameter snapshot: 2026-08. If a call rejects a parameter shown here, trust
the API error and check the vendor's current docs.

## Fetching pages (known URLs)

Both services can fetch known URLs; they failed differently on our five-site
anti-bot test (Discourse forum, X profile, zhihu, bilibili, tieba):

- **Tavily `/extract`** — `{"urls": ["https://..."]}`. Pulled full content
  from the Discourse forum (30KB) and the X profile (real tweets); hit walls
  on zhihu (login page), bilibili (JS-only skeleton), and tieba (refused).
- **Exa `/contents`** — a documented retrieval endpoint for known URLs,
  strongest for pages already in its index. Its forced-live mode
  (`maxAgeHours: 0`) returned nothing useful on all five test sites — that
  indicts hostile-target live fetching, not the endpoint in general.

Rule of thumb: for the five anti-bot/JS-heavy targets tested, Tavily
`/extract` succeeded 2/5 and Exa `/contents` 0/5 — try Tavily first for
similar targets, but treat that as a test-set result, not a general provider
capability rule. Exa `/contents` is fine for ordinary public pages,
especially indexed ones. Validate whatever comes back — login walls and JS
skeletons arrive looking like "content". If both fail, search for the
material instead: forum posts get quoted, summarized, and reposted
elsewhere.

## Using both (second-opinion pattern)

The indexes barely overlap, but that alone doesn't justify doubling cost —
run both only for high-impact questions, explicit broad-coverage asks, or
when the first service's evidence is weak, stale, or low-authority. When you
do:

1. Query Exa for dated, primary sources; query Tavily for community threads.
2. Merge; dedupe by domain+path (exact-URL dedupe misses cross-postings).
3. Carry over Exa's `publishedDate` and Tavily's `score` as merge metadata.
4. Order by: primary source + recent date first, then scored community posts.

## Known limits (community-confirmed)

- **Forum/social-heavy research:** both services are considered weak here by
  practitioner consensus; between the two, Tavily is the better pick. Don't
  expect exhaustive forum coverage from either.
- **Tavily free tier rate limits:** the 1,000 credits/month plan 429s
  aggressively under bursts — sometimes surfacing as empty responses rather
  than errors. Batch calls with backoff, or budget for a paid tier.
- **Exa pricing drift:** prices rose $5→$7/1k in 2026-03 and the table is
  multi-part (search + per-result + per-content-type). Check `costDollars`
  in responses when cost matters.

## Common mistakes

1. **Assuming either service can fetch anything.** Exa `/contents` does
   retrieve known URLs (best for indexed pages); our five-site anti-bot test
   showed its forced-live mode going 0/5 while Tavily `/extract` went 2/5.
   Try Tavily first on hostile targets, validate what comes back, and expect
   both to fail on login walls and JS-only pages.
2. **Tavily `fast`/`ultra-fast` "for speed".** Measured slower or equal to
   `basic`, with degraded results.
3. **Exa `category: company` / `people` with date filters.** HTTP 400 — these
   categories use dedicated indices without date support.
4. **Trusting Tavily dates.** `published_date` is almost never populated
   (0/159 results in testing). If freshness matters, filter on Exa.
5. **Using deprecated Exa parameters** (`neural`/`keyword`, `livecrawl`) —
   current equivalents are listed in `references/exa.md`.
6. **Exa `contents` billing.** Each content type is billed per page —
   `text` + `highlights` on the same page costs 2 pages.
7. **`deep-lite` as a quality upgrade.** In tests it did not beat `auto`; it
   costs 1.7x and takes 4-8x longer.

## References

- `references/tavily.md` — full parameter tables, endpoints, recipes, pricing
- `references/exa.md` — full parameter tables, contents options, `outputSchema`
  examples, categories, pricing
- `references/evidence.md` — the measured data behind every rule above
  (batch tests, latency, mode quality, feature verification, anti-block matrix)
- `references/community-feedback.md` — practitioner opinions and known-good/
  known-bad reports from HN, Reddit, linux.do (~40 sources)
