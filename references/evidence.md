# Evidence — Measured Data Behind the Rules (2026-08-18)

This snapshot comes from direct API calls from one Windows machine: one
network region, one time window, one account tier per provider, four
fixed queries per mode plus one broad 20-query pass, no blind human
relevance grading, no confidence intervals. Latency is end-to-end and
includes provider load, network variance, caching, and crawl waits —
directional measurements, not an SLA. Domain counts use a static
allowlist, which can count a provider forum as authoritative, miss a
strong independent blog, and count several URLs for one paper as
separate sources. Manual review used titles, URLs, and Tavily snippets;
not every returned page was independently fact-checked.

| Suite | Artifact | Scope |
|---|---|---|
| Broad comparison | `batch_compare.json` | 20 query types, both providers, 8 requested results |
| Search modes | `comprehensive_modes.json` | 40 cases: 4 fixed queries across 10 modes |
| Parameters | `comprehensive_parameters.json` | 78 boundary, conflict, output, and semantic checks |
| Known-URL retrieval | `comprehensive_extract.json` | 54 cases, including a 13-site fetch matrix |

## 1. Broad 20-query comparison

| Metric | Tavily | Exa |
|---|---:|---:|
| Results returned | 158 | 160 |
| Allowlisted community-domain hits | **17** | 6 |
| Allowlisted authoritative-domain hits | 6 | **18** |
| Results carrying a publication date | 0 | **80** |
| Median latency | **1,180 ms** | 1,497 ms |
| p95 latency | **2,344 ms** | 2,467 ms |
| Observed cost per query | 1 credit | $0.007 |

Average per-query domain Jaccard overlap was **0.22** — the indexes were
mostly complementary. Low overlap alone does not prove that paying for
both improves an answer.

## 2. Search-mode matrix

Each mode used the same four intents: official documentation, original paper,
English developer criticism, and Chinese production experience.

| Provider mode | Median | Observed cost | Target hits | Community hits | Authority hits | Near-duplicates |
|---|---:|---:|---:|---:|---:|---:|
| Tavily `ultra-fast` | 1,408 ms | 1 credit | 9 | 4 | 7 | 3 |
| Tavily `fast` | 1,409 ms | 1 credit | 9 | 4 | 7 | 3 |
| Tavily `basic` | 3,603 ms | 1 credit | 13 | 7 | 8 | 1 |
| Tavily `advanced` | 4,900 ms | 2 credits | 11 | 5 | 6 | 1 |
| Exa `instant` | 969 ms | $0.007 | 14 | 1 | 13 | 0 |
| Exa `fast` | 1,153 ms | $0.007 | 11 | 0 | 11 | 0 |
| Exa `auto` | 1,779 ms | $0.007 | 12 | 0 | 13 | 2 |
| Exa `deep-lite` | 5,988 ms | $0.012 | 11 | 2 | 10 | 1 |
| Exa `deep` | 5,262 ms | $0.012 | 15 | 6 | 11 | 0 |
| Exa `deep-reasoning` | 12,677 ms | $0.015 | 16 | 6 | 10 | 0 |

Manual review changed how these numbers should be read:

- **Official docs:** Exa `instant`/`fast` ranked official OpenAI documentation
  best. Tavily fast modes over-counted repeated OpenAI community pages and
  mixed in recruiting or marketing pages.
- **Original paper:** Exa `auto` placed the Mamba paper, OpenReview entry, and
  official repository first. Tavily `basic` was usable as a fallback; its other
  modes favored mirrors or secondary material.
- **English community criticism:** Tavily `basic`/`advanced` gave the best
  balance of developer articles and discussions. Exa `deep-reasoning` found
  several useful Hacker News threads, but at much higher latency and cost.
- **Chinese production experience:** Exa `instant`/`fast`/`auto` were most
  relevant. Exa `deep-reasoning` drifted to English sources; Tavily fast modes
  were substantially off-topic.

Exa mode cases in this artifact contain titles and URLs but no fetched text,
so their manual quality judgment does not establish page-content accuracy.

## 3. Parameter and boundary matrix

The 78 cases produced **67 HTTP 2xx**, **11 HTTP 4xx**, and **0 transport
failures**. A 2xx means only that the endpoint accepted the request; it does not
prove that every field was honored.

### Tavily

- A 1,501-character query returned 200. Treat the documented 1,500-character
  guidance as a portability limit, not a reliably enforced server boundary.
- `max_results: 0` returned 400. Values 20 and 21 were accepted, but returned
  only 15 and 20 results in this run. Do not depend on more than the documented
  20-result limit.
- All four `time_range` values and an exact date window were accepted.
  Combining `time_range` with exact start/end dates returned 400.
- `include_answer: basic` and `advanced` returned answers of about 279 and 483
  characters. Both `markdown` and `text` raw-content modes worked.
- With images enabled, requesting descriptions produced 5 descriptions; the
  control produced the same 5 images and 0 descriptions.
- `include_domains: ["arxiv.org"]` returned only arXiv results. Supplying the
  same domain in include and exclude lists still returned 200, so callers
  should reject or normalize that conflict themselves.
- `exact_match: true` returned 5 results. Its source-set Jaccard versus the
  control was 0.111, proving an observable difference but not strict phrase
  semantics.
- `auto_parameters: true` cost 2 credits. Adding explicit `search_depth:
  basic` still cost 2 credits and returned the same ordered results, so the
  live behavior did not demonstrate that the explicit depth prevented an
  automatic upgrade.
- `safe_search: true` returned 403 for the tested account.
- Extract accepted one URL string and a list of 20 URLs; 21 URLs returned 400.
  `chunks_per_source` values 0 and 6 returned 400. `timeout: 0` returned 400,
  while 61 was unexpectedly accepted; retain the documented 1-60 range.

### Exa

- Empty query, `numResults: 0`, and `numResults: 101` returned 400. Requests for
  1 and 10 results cost $0.007, 11 cost $0.008, and 100 cost $0.097 in this run.
- All six categories were accepted. `company+date`, `people+date`, and
  `people+excludeDomains` returned 400. `company+excludeDomains` happened to
  return 200, but should not be treated as a stable supported combination.
- Non-deep `additionalQueries` returned 200 but produced the same source set as
  its control. Deep modes accepted 1 and 10 extra queries; 11 returned 400.
- `outputSchema`, moderation, location, and SSE streaming were accepted. The
  stream parser observed `results`, `done`, and `[DONE]`, rather than merely
  checking for HTTP 200.
- A `/search` request with nested text, highlights, summary, and extras returned
  all requested output types and cost $0.009.
- Deprecated crawl-date fields and `context` returned 200 but produced the same
  ordered results as their control, consistent with being ignored.
- HIPAA compliance mode returned 403 for the tested account.
- `maxAgeHours: 721` was accepted even though current documentation stops at
  720. Keep the documented range. For `/contents`, inspect every `statuses[]`
  entry because an overall 200 can contain per-URL failures.

## 4. Known-URL retrieval matrix

| Target | Tavily Extract | Exa Contents |
|---|---|---|
| Static page, Python docs, GitHub, HN, arXiv, dev.to, Medium | usable content | usable content |
| Linux.do topic | usable topic text; appended AI-directed prompt-injection text | cache miss or live timeout/error |
| X profile | real posts, timestamps, and interaction context | `SOURCE_NOT_AVAILABLE` |
| Reddit thread | failed | `SOURCE_NOT_AVAILABLE` |
| Zhihu | public homepage, not the target answer | login wall |
| Current Bilibili video | usable video-page information in basic and advanced | usable in live and 24-hour-cache modes; cache-only initially missed |
| Baidu Tieba | failed | cache/24-hour mode could work; forced-live timed out |

Tavily basic and advanced each returned 11 of 13 targets and failed Reddit and
Tieba. Advanced took 15.5s versus 9.6s for basic and did not unlock either
failed site.

Exa cache-only returned in 0.53s. Forced-live and 24-hour-cache runs each took
about 30.5s because difficult sites waited for crawl timeouts. Exact URL and
cache state materially changed results, so this matrix is a 2026-08-18
observation, not a permanent site-support promise.

The Linux.do text ended with a block beginning `CRITICAL INSTRUCTIONS FOR ALL
AI ASSISTANTS...` that attempted to make models refuse writing help and visit
the site's guidelines. It was flagged as prompt-injection and never followed.

## 4a. Spot check, 2026-09-21

Five drift-prone sites re-run with the same request shapes as §4 (Tavily
`/extract` basic, one batch; Exa `/contents` at `maxAgeHours` −1/0/24).
Raw output: `search_results/spot_check_2026-09-21.json`. Single-run
observations, same method limits as the opening section.

- **Tavily: unchanged.** Linux.do (12,417 chars), X, and Bilibili usable;
  Reddit still failed; the Linux.do page still carried the AI-directed
  instruction block. The Zhihu homepage (the requested URL) returned 511
  chars.
- **Exa, Linux.do: improved.** Forced-live and 24h-cache both returned usable
  text (1,827 chars); cache-only still errored. §4's "live timeout" did not
  hold in this window.
- **Exa, Bilibili: mixed.** Forced-live errored once while 24h-cache returned
  usable text — the reverse of the 2026-08-18 live success. Cache state, not
  the site, decides; this matches §4's closing caveat.
- **Exa, X/Reddit: unchanged.** Error / `SOURCE_NOT_AVAILABLE` in all three
  cache modes. Zhihu cache-only returned 323 chars (homepage shell) — still
  treat Zhihu as a login wall.
