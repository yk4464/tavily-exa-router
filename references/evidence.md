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
not every returned page was independently fact-checked. Each section is a
dated snapshot; later findings are appended as dated notes instead of
rewriting the earlier record.

| Suite | Artifact | Scope |
|---|---|---|
| Broad comparison | `batch_compare.json` | 20 query types, both providers, 8 requested results |
| Search modes | `comprehensive_modes.json` | 40 cases: 4 fixed queries across 10 modes |
| Parameters | `comprehensive_parameters.json` | 78 boundary, conflict, output, and semantic checks |
| Known-URL retrieval | `comprehensive_extract.json` | 54 cases, including a 13-site fetch matrix |

## Contents

- §1 Broad 20-query comparison — volume, dates, latency, cost, domain overlap
- §2 Search-mode matrix — 10 modes × 4 fixed intents, plus manual review
- §3 Parameter and boundary matrix — 78 cases (Tavily, then Exa)
- §4 Known-URL retrieval matrix — 13 sites × both providers (2026-08-18)
- §4a Spot check, 2026-09-21 — 5 drift-prone sites re-run
- §4b Injection survey, 2026-09-25 — 11 pages × both providers, tail-append vs whole-body
- §5 Full re-run, 2026-10-03 — dual-network regression, drift findings, updated latencies
- §6 Targeted audit, 2026-10-06 — single-run checks behind the 2026-10-06 rule changes
- §7 Exa `lite` vs legacy types, 2026-10-31 — blind quality, dates, contents, windows, per-class defaults

## 1. Broad 20-query comparison

| Metric | Tavily | Exa |
|---|---:|---:|
| Results returned | 158 | 160 |
| Allowlisted community-domain hits | **17** | 6 |
| Allowlisted authoritative-domain hits | 6 | **18** |
| Results carrying a publication date | 0 † | **80** |
| Median latency | **1,180 ms** | 1,497 ms |
| p95 latency | **2,344 ms** | 2,467 ms |
| Observed cost per query | 1 credit | $0.007 |

† **Caveat on the Tavily date zero (found 2026-10-06):** `tests/batch_compare.py`
stored a literal `None` for every Tavily result's date field instead of reading
`published_date` from the response, while the Exa side did read the real
`publishedDate`. So this zero measures the collector, not necessarily the API —
it cannot be used as evidence that Tavily returns no dates. A 2026-10-06 spot
check did return 0 dated results out of 8 on a general product query, which is
consistent, but one query is not the 158-result sample.

**Documentation check, 2026-10-31:** Tavily's current `/search` reference
documents `include_published_date` (default `false`, currently beta, enabled
automatically for `topic: news`) and `filter_by_published_date` (removes
results outside the requested window, including results with no detectable
date; setting it true also enables `include_published_date`). Neither this
broad run nor the 2026-10-06 spot check set `include_published_date`, so a
zero dated-result count does not show that the API cannot return dates.
Source: https://docs.tavily.com/documentation/api-reference/endpoint/search

Average per-query domain Jaccard overlap was **0.22** — the indexes were
mostly complementary. Low overlap alone does not prove that paying for
both improves an answer.

## 2. Search-mode matrix

Each mode used the same four intents: official documentation, original paper,
English developer criticism, and Chinese production experience.

| Provider mode | Median | Observed cost | Target hits | Community hits | Authority hits | Near-duplicates †† |
|---|---:|---:|---:|---:|---:|---:|
| Tavily `ultra-fast` | 1,408 ms | 1 credit | 9 | 4 | 7 | 3 |
| Tavily `fast` | 1,409 ms | 1 credit | 9 | 4 | 7 | 3 |
| Tavily `basic` | 3,603 ms | 1 credit | 13 | 7 | 8 | 1 |
| Tavily `advanced` | 4,900 ms | 2 credits | 11 | 5 | 6 | 1 |
| Exa `instant` | 969 ms | $0.007 ‡ | 14 | 1 | 13 | 0 |
| Exa `fast` | 1,153 ms | $0.007 | 11 | 0 | 11 | 0 |
| Exa `auto` | 1,779 ms | $0.007 | 12 | 0 | 13 | 2 |
| Exa `deep-lite` | 5,988 ms | $0.012 | 11 | 2 | 10 | 1 |
| Exa `deep` | 5,262 ms | $0.012 | 15 | 6 | 11 | 0 |
| Exa `deep-reasoning` | 12,677 ms | $0.015 | 16 | 6 | 10 | 0 |

‡ This is the per-request `costDollars` observed on 2026-08-18. Three live
`instant` requests on 2026-10-06 billed USD 0.004 each (USD 4/1k), not
USD 0.007; see §6.

†† Near-duplicates are the `near_duplicate_urls` count from
`tests/comprehensive_benchmark.py` as it stood for this run. That formula also
treated exact duplicates as near-duplicates, so the column is not a count of
distinct-but-similar pages and is not comparable with a stricter duplicate
definition. Historical values are kept as measured. From 2026-10-31 the script
uses a same-source-only definition that excludes exact duplicates, so later
counts are not directly comparable with these stored values.

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
  Official-reference check, 2026-10-31: the current spec forbids
  `startPublishedDate`/`endPublishedDate` for both `company` and `people`,
  and `excludeDomains` only for `people`; it does not prohibit
  `company+excludeDomains`. The pair is therefore allowed by the contract,
  and the 200 is consistent with it; it remains a single-account
  observation rather than a promise
  (https://exa.ai/docs/reference/search). This supersedes the "not a stable
  supported combination" reading above.
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
Raw output: `search_results/spot_check_2026-09-21.json` — **artifact not
retained**: `search_results/` is gitignored and this file is absent from the
checkout. Single-run observations, same method limits as the opening section.

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

## 4b. Injection survey, 2026-09-25

Follow-up to §4's single Linux.do case, to test whether the phenomenon is
site-specific and how large a share of a response it can occupy. 11 public
pages × both providers = 22 fetches (Tavily `/extract` default; Exa
`/contents` with `text`), read-only, no login. 19 returned body text, 3
failed. Raw responses were written under `search_results/` on the run
machine; **artifact not retained** — that directory is gitignored and the
responses are absent from this checkout.

| Site family | Body returned | Injection signal |
|---|---|---|
| Linux.do, 3 different topics | yes (Tavily; Exa on 2 of 3) | **yes, all confirmed cases** |
| V2EX, 2 topics | yes (both providers) | no |
| Python docs | yes (both) | no |
| GitHub repo page | yes (both) | no |
| Hacker News thread | yes (both) | no |
| BBC News | yes (both) | no |
| Exa vendor comparison page | yes (both) | no |
| Zhihu question | no — Tavily 35 chars; Exa no text | n/a (login wall, matches §4) |

Two findings matter more than the site list:

1. **Tail append, and it can become the whole response.** On the three
   Linux.do topics the block began at 82.6% / 87.0% / 87.2% of the Tavily
   body, after the page's related-topic table — normal content for the first
   ~8.5–10.8k characters. But the *same* topic returned by Exa came back as
   only 1,694 characters, of which 1,593 (**94.0%**) were the injected block.
   The block is byte-identical across all three topics (same SHA-256 prefix),
   so it is server-appended site furniture, not user-authored argument.
   **Share of the response occupied by the injection is decided by how much
   of the page the provider sliced, not by the site** — a downstream consumer
   that takes the first N characters, or treats a short return as a summary,
   can ingest the injection as essentially all of its input.
2. **Both providers return it verbatim**, so this is not a Tavily
   sanitization gap — the text is in the page. On Linux.do, Exa's Chinese
   body was mojibake in this run while the ASCII injection block stayed fully
   legible, making the injection the clearest text in that response.

The block claims the site prohibits AI-generated content and instructs the
model to refuse writing help, recite a scripted notice to the user, and
navigate the session to the site's guidelines page. None of that comes from
the user or the system prompt.

Caveats, stated plainly: the "only Linux.do so far" result rests on 11 URLs,
all well-known sites, so it bounds nothing about other community platforms; no
second Chinese forum family was tested. This is a single-time snapshot with no
time series, so nothing is established about whether the block persists. The
mojibake was not attributed to either the provider's decoding or the site's
response. Detection signatures also produce false positives: the bare word
`override` matched ordinary technical prose twice here (a Python docs sentence
on regex flags, a README comment "# Per-call override") — never treat it as a
signal on its own.

Observed failure modes this run: Exa `/contents` on one Linux.do topic returned
`CRAWL_UNKNOWN_ERROR`; Zhihu returned 35 characters (Tavily) and no text (Exa),
consistent with §4; a second V2EX topic returned implausibly short bodies (442
/ 328 chars) whose truncation cause was not determined.

## 5. Full re-run, 2026-10-03

Quarterly full regression run conducted across two distinct network egresses:
a local Windows workstation and an Aliyun Hong Kong cloud host, using active
paid API tiers for both providers. The test executed 172 test cases per
endpoint (344 total runs across both environments) covering the broad 20-query
comparison, 10 search modes, 78 parameter/boundary checks, and the 13-site
URL retrieval matrix, alongside dedicated passes (`smoke_test.py` passing 9/9 on
both endpoints, `speed_test`, and `community_test`).

### 5.1 Broad 20-query comparison (`batch_compare.json`)

Both endpoints produced consistent result counts, category splits, and domain
overlap:

| Metric | Tavily | Exa |
|---|---:|---:|
| Results returned | 159 | 158 |
| Allowlisted community-domain hits | **16** | 6–7 |
| Allowlisted authoritative-domain hits | 7 | **20–23** |
| Results carrying a publication date | 0 † | **77–84** |
| Median latency (Local Windows) | 3,146 ms | 2,866 ms |
| Median latency (Aliyun Hong Kong) | **644 ms** | **2,040 ms** |
| Observed cost per query | 1 credit | $0.007 |

Average per-query domain Jaccard overlap dropped to **0.12** (identical across
both network endpoints; down from 0.22 in the 2026-08-18 baseline). The two
indexes remain sharply differentiated and complementary.

† The Tavily zero has the same collector caveat as §1: `batch_compare.py`
stored a literal `None` for Tavily dates, and this run did not enable Tavily's
`include_published_date`. It is not evidence that Tavily omits dates; see the
2026-10-31 documentation check in §1.

### 5.2 Search-mode latency and quality matrix

Median end-to-end latencies (ms) across four passes: baseline (2026-08-18), Local
Round 1, Local Round 2, and Aliyun Hong Kong:

| Mode | 2026-08-18 Baseline | Local R1 | Local R2 | Aliyun HK | Target hits (exp/comm/auth) |
|---|---:|---:|---:|---:|---:|
| Tavily `ultra-fast` | 1,408 ms | 1,834 ms | 1,823 ms | 784 ms | — |
| Tavily `fast` | 1,409 ms | 2,053 ms | 2,047 ms | 646 ms | — |
| Tavily `basic` | 3,603 ms | 3,617 ms | 2,353 ms | 640 ms | 15 / 8 / 8 |
| Tavily `advanced` | 4,900 ms | 4,588 ms | 2,722 ms | 772 ms | 14–15 / 7 / 7–8 |
| Exa `instant` | 969 ms | 1,372 ms | 1,114 ms | 466 ms | 8 / 1 / 8–9 |
| Exa `fast` | 1,153 ms | 1,832 ms | 1,148 ms | 566 ms | 9 / 2 / 10 |
| Exa `auto` | 1,779 ms | 2,570 ms | 1,137 ms | 1,594 ms | 9–10 / 2–3 / 9–10 |
| Exa `deep-lite` | 5,988 ms | 5,469 ms | 3,312 ms | 3,765 ms | 8–11 / 1–2 / 8–10 |
| Exa `deep` | 5,262 ms | 11,569 ms | 9,780 ms | 8,457 ms | 14–16 / 5–8 / 8–11 |
| Exa `deep-reasoning` | 12,677 ms | 11,755 ms | 13,536 ms | 14,261 ms | 12–17 / 2–8 / 8–10 |

In dedicated `speed_test` runs (completed cleanly from Hong Kong; local runs
aborted due to local SSL EOF errors), Exa `auto` median was 237 ms, `instant`
363 ms, and `deep-lite` 2,768 ms; Tavily `ultra-fast` was 773 ms, `fast` 953 ms,
`basic` 2,220 ms, and `advanced` 5,018 ms.

Key mode observations:
- Latencies are highly egress-sensitive: Tavily basic drops from ~3.6s locally to
  640 ms in Hong Kong; Exa instant drops from ~1.1–1.4s locally to 466 ms in HK.
- **Exa `deep` experienced genuine server-side latency drift**: 5.3s in August
  ballooned to ~8.5–11.6s across all test runs and egresses, while
  `deep-reasoning` remained in the ~11.8–14.3s range.
- Mode hit qualities remained aligned with baseline: Tavily `advanced` continues
  to provide no quality improvement over `basic` (14–15 vs 15 target hits)
  despite costing 2 credits. Exa `deep-lite` remains an inferior value compared
  to `auto`.

### 5.3 Parameter boundary checks and drift observations

All baseline boundary and edge findings were reproduced across both endpoints:
- Exa category conflicts: `company` + date filters, `people` + date filters, and
  `people` + `excludeDomains` consistently return HTTP 400.
  `company` + `excludeDomains` returned HTTP 200 on both sides, confirming
  it as undocumented vendor drift rather than a reliable contract.
- Tavily accepted boundary values: 1,501-character queries, `max_results: 21`,
  and `timeout: 61` were all accepted without rejection.
- Exa boundaries: `numResults: 101` and `additionalQueries: 11` were accepted;
  requesting HIPAA compliance returned HTTP 403.
- Deprecated Exa parameters (`neural`/`keyword`, `context`, `startCrawlDate`/`endCrawlDate`,
  `livecrawl`) returned HTTP 200 but were silently ignored (Jaccard 1.0 against
  controls).
- Tavily `auto_parameters` with explicit `search_depth: basic` still billed 2
  credits and returned identical results (`same_order: true`) to basic.

**Correction, 2026-10-06.** Two entries above are superseded; every other
2026-10-03 finding is kept as recorded. The full 2026-10-06 checklist is in
§6.

- **`numResults: 101` / `additionalQueries: 11` were rejected, not accepted.**
  The stored 2026-10-03 artifacts (`search_results/comprehensive_benchmark.json`
  and `search_results/comprehensive_run1_local.json`) record HTTP 400 for both:
  `NUM_RESULTS_EXCEEDED` ("You are asking for a number of results above what
  your plan allows") and a validation error, "Too big: expected array to have
  <=10 items at \"additionalQueries\"". Both stored endpoint runs show 400.
- **The deprecated-parameter claim was wider than the controls.** Only the
  `startCrawlDate`/`endCrawlDate` and `context` pairs were actually compared
  with controls (Jaccard 1.0). `neural`, `keyword`, and legacy `livecrawl` were
  not verified as ignored. On 2026-10-06 `neural` and `keyword` returned HTTP
  200 with visibly different result sets and different billing (0.004 vs
  0.007); deprecated does not mean inert (§6).

**Official-reference check, 2026-10-31.** The current Exa `/search` reference
forbids `startPublishedDate`/`endPublishedDate` for both `company` and
`people`, and `excludeDomains` only for `people`; it allows
`company` + `excludeDomains` because only the listed restrictions are
rejected. The three HTTP 200 observations (2026-08-18, 2026-10-03,
2026-10-06) are consistent with that contract; this supersedes the
"undocumented vendor drift" label in the first bullet. Source:
https://exa.ai/docs/reference/search

Three new drifts were observed:
1. **`safe_search` now returns HTTP 200**: In August 2026 this account returned
   HTTP 403; on 2026-10-03 both endpoints succeeded with HTTP 200.
2. **`resolvedSearchType` reappeared in Exa responses**: Previously audited as
   removed in 2026-04/05, the field was present in 2026-10-03 responses.
3. **`exact_match` behavior is unstable**: On Local Round 1, the test query
   returned 0 results (Jaccard 0.0 against control); on Local Round 2, it
   returned 5 results. Do not treat `exact_match` as dependable across runs.

### 5.4 Known-URL retrieval matrix (13 sites)

Results were identical across both network endpoints:
- **Tavily `/extract` succeeded on 11/13 sites**: Reddit and Tieba still fail
  consistently. Zhihu returned a 35-character login wall/homepage shell instead
  of target answers. Linux.do succeeded but continued to return the injected
  tail block.
- **Exa `/contents`**:
  - Cached retrieval (`maxAgeHours: -1` or `24`) succeeded on both Bilibili and
    Tieba.
  - X (Twitter) and Reddit remain blocked with `SOURCE_NOT_AVAILABLE`.
  - Forced live fetching (`maxAgeHours: 0`) became flaky rather than a
    guaranteed 30s timeout: all difficult sites resolved in <13s, but Linux.do
    threw `CRAWL_UNKNOWN_ERROR` on the Hong Kong host (succeeded locally), and
    Tieba live fetch returned HTTP 500 across both endpoints.

### 5.5 Caveats and operational notes

1. **Local egress network instability**: The local Windows test environment
   encountered two transient SSL EOF disconnects (on the first query of
   `search_compare` and during `speed_test`). Hong Kong cloud execution ran
   cleanly without connection drops.
2. **Community test variance**: In the dedicated `community_test`, Chinese forum
   queries via Tavily returned off-topic filler (investing.com and gaming sites)
   across both runs, while Exa Chinese recall remained coherent. This is noted as
   a single-snapshot caveat requiring follow-up verification before altering
   routing weights.
3. **Benchmark script compatibility**: The benchmark script
   `tests/comprehensive_benchmark.py` previously failed with a `SyntaxError` on
   Python ≤3.11 due to backslashes inside f-string expressions; this was fixed
   in this regression cycle.

## 6. Targeted audit, 2026-10-06

Focused checks behind the 2026-10-06 rule, price, and parameter changes. Raw
artifacts not retained; these are single-run observations as recorded in
commit `b386ed7` (the 2026-10-06 audit) and repeated in `SKILL.md`,
`CHANGELOG.md`, `references/exa.md`, and `references/tavily.md`. One account,
one network region, no repeated trials — point observations, not a regression
suite.

### Exa

- **`instant` billing:** three live requests returned `costDollars.total`
  0.004 each (USD 4/1k), not the USD 0.007 recorded for 2026-08-18 in §2.
  The current price table lists `auto` and `fast` at USD 0.007, `deep-lite`
  and `deep` at USD 0.012, and `deep-reasoning` at USD 0.015; the deep prices
  were re-verified in the same pass.
- **Results beyond 10:** `numResults: 50` returned 50 results for USD 0.047
  (6.7× the USD 0.007 base); `numResults: 100` returned 99 results for
  USD 0.096 (13.7×). Billing tracks the returned count, not the requested
  count.
- **Standalone `/contents`:** one URL with `text` + `highlights` billed 0.002;
  adding `summary` billed 0.003. There is no flat per-URL price.
- **`outputSchema`:** added about 2 seconds of latency and left
  `costDollars` unchanged — no separate charge.
- **`startPublishedDate`:** a lower bound set to the current instant returned
  only same-day third-party posts; a one-week bound surfaced the previous
  day's official announcement. Use the start of the user's window.
- **`company` + `excludeDomains`:** returned HTTP 200, the third such
  observation after 2026-08-18 and 2026-10-03. The current contract allows
  this pair (dates are forbidden for `company` and `people`, and
  `excludeDomains` only for `people`), so the 200 is consistent with it —
  see §3 and §5.3.
- **Legacy `neural` / `keyword`:** both returned HTTP 200 with visibly
  different result sets and different billing (0.004 vs 0.007). Deprecated
  does not mean inert.
- **`resolvedSearchType`:** present as `""` in every response. The field is
  deprecated and may be empty; do not branch on it.

### Tavily

- **`include_answer: "advanced"`:** at `search_depth: basic` it billed 1
  credit, the same as `basic`, and was not reliably longer. It changes detail
  granularity, not the credit price.
- **`max_results` default:** with the parameter omitted, the account returned
  10 results, measured twice. Vendor pages disagree on the default (5 vs 10);
  set it explicitly.
- **`safe_search` depth limit:** `safe_search: true` with `search_depth:
  fast` or `ultra-fast` returned HTTP 400.
- **Search snippets carry page content:** a Tavily search for a page with a
  known injection returned that injection inside `results[].content` at
  `score` ≈ 0.81, with no `/extract` call. Injection handling applies to
  search responses, not just fetched bodies.
- **A low score can be the right result:** a query for one specific
  discussion returned that discussion at `score` ≈ 0.06. Score is triage,
  not a correctness threshold.

### Merge behavior

- **Dedupe on the full URL:** Hacker News threads share domain and path and
  differ only by `?id=`. Keying on domain+path collapsed 8 distinct
  discussions into 1; the full URL keeps them apart.

**Conclusion**: The core routing conclusions remain fully valid: community
queries route to Tavily, official documentation and dated queries route to Exa,
and all known boundary pitfalls persist. Latency figures are highly network-sensitive,
while Exa `deep` slowdown represents genuine vendor-side drift.

## 7. Exa `lite` vs legacy types, 2026-10-31

Single-egress measurement from one local Windows workstation (no Hong Kong
host was reachable in this cycle). Eighteen queries — six current-events, six
academic, six Chinese — each went through Exa `lite`, legacy `instant`,
legacy `fast`, and `auto` with `numResults: 8`, three latency samples per
query/type. The run also covered 90 contents calls (`lite`/`instant`/`auto`
with `highlights` or `text`), 15 `startPublishedDate` probes, the two
documented `lite` 400s, and 9 Tavily searches. A first contents/Tavily pass
was re-run after fixing the collector's Tavily date field (`published_date`
versus Exa's `publishedDate`); the retained artifact and the numbers here are
from the fixed pass. A second full pass returned identical URL sets for all
72 query/type pairs (mean Jaccard 1.0; counts and dated shares matched), so
the quality and date tables apply to both. API spend was about USD 3.63 on
Exa plus 37 Tavily credits (including two collector-fix passes and a raw
field spot check); the blind judge cost USD 0.0041. Raw responses
are in `search_results/lite_quality.json` (git-ignored, not committed); the
query list is `tests/lite_quality_test.py`.

Quality was judged blind: one state per unique (query, URL) pair (158 pairs),
with the producing search type removed. A judge model (`typesafe/jev-1.14.0`)
scored each result 0–3 for relevance and 0–3 for authority; per-query means
over the top five were averaged across the six queries in each class. Scores
are model judgments over titles, URLs, and dates — not page-content checks.

### 7.1 Blind quality

| Class | Type | Relevance | Authority | Relevant in top 5 |
|---|---|---:|---:|---:|
| news | `lite` | 2.55 | 1.64 | 4.50 |
| news | `instant` | 2.65 | 1.75 | 4.67 |
| news | `fast` | 2.55 | 1.64 | 4.50 |
| news | `auto` | 2.52 | 1.58 | 4.33 |
| academic | `lite` | 2.72 | 2.71 | 4.83 |
| academic | `instant` | 2.74 | 2.74 | 5.00 |
| academic | `fast` | 2.72 | 2.71 | 4.83 |
| academic | `auto` | 2.72 | 2.71 | 4.83 |
| Chinese | `lite` | 2.51 | 2.03 | 4.33 |
| Chinese | `instant` | 2.58 | 1.93 | 4.50 |
| Chinese | `fast` | 2.51 | 2.03 | 4.33 |
| Chinese | `auto` | 2.51 | 2.03 | 4.33 |

Paired differences, `instant` − `lite`, per-class mean over six queries with a
20,000-resample bootstrap 95% interval:

| Class | Relevance | Authority | Relevant top-5 |
|---|---|---|---|
| news | +0.10 [−0.07, +0.23] | +0.11 [−0.07, +0.29] | +0.17 [−0.33, +0.67] |
| academic | +0.02 [−0.09, +0.11] | +0.03 [−0.02, +0.12] | +0.17 [0.00, +0.50] |
| Chinese | +0.07 [−0.02, +0.20] | −0.10 [−0.24, +0.03] | +0.17 [0.00, +0.50] |

Allowlisted-domain hits over the 48 results per class (same coarse lists as
§1; supporting evidence, not the decision):

| Class | `lite` auth/comm | `instant` auth/comm | `fast` auth/comm | `auto` auth/comm |
|---|---|---|---|---|
| news | 7 / 0 | 9 / 0 | 7 / 0 | 7 / 0 |
| academic | 15 / 0 | 19 / 0 | 15 / 0 | 15 / 0 |
| Chinese | 11 / 2 | 8 / 1 | 11 / 2 | 11 / 2 |

Every relevance and authority interval includes zero, and every absolute
difference is below 0.2 points on the 0–3 scale. `lite`, `fast`, and `auto`
returned nearly identical URL sets (mean Jaccard 0.988 for `lite` vs `fast`
and `lite` vs `auto`), so their scores are the same results judged once;
`instant` returned a different set (0.199 vs `lite`). No quality winner
emerges at this sample size.

### 7.2 Publication-date coverage

Share of returned results carrying `publishedDate` (48 results per class):

| Class | `lite` | `instant` | `fast` | `auto` | `instant` − `lite` |
|---|---:|---:|---:|---:|---:|
| news | 64.6% | 75.0% | 64.6% | 64.6% | +10.4 pp [2.1, 18.8] |
| academic | 29.2% | 52.1% | 31.2% | 31.2% | +22.9 pp [6.2, 39.6] |
| Chinese | 52.1% | 77.1% | 52.1% | 52.1% | +25.0 pp [8.3, 39.6] |

`fast` and `auto` track `lite`, not `instant`. The gap is mostly result-set
composition, not a stripped field: on the eight URLs that `lite` and
`instant` shared, `instant` had a date for seven and `lite` omitted it for
one.

`startPublishedDate` windows held in all nine seven-day probes (one query per
class × `lite`/`instant`/`auto`): 8/8 results dated and zero results before the
bound. A lower bound set to the request instant did **not** error, but
collapsed recall to 5 results (news) or 6 (academic, Chinese); all were dated
the same day or up to seven days ahead (`2026-11-02` to `2026-11-07` versus a
2026-10-31 request). The bound is enforced; setting it to "now" buys a
same-day slice and can surface future-dated metadata. Use the start of the
user's window.

### 7.3 Contents requests

Counts stayed at 8/8 in every one of the 90 contents calls; `lite` never
returned fewer results than `instant` with the same `highlights`/`text`
request (0% drop in all 18 paired queries). All 144 results in the `lite`
highlights calls carried a highlight, and all 144 in the `lite` text calls
carried text (minimum 93 characters, median 1,200 at the request cap), so the
documented "uncached results are left out" rule did not trigger for these
popular queries. It is not evidence that the rule never triggers.

The set still moved: URL overlap with the plain `lite` response was 0.914 for
`highlights` and 0.697 for `text`. A `text` request replaced about 30% of the
top-eight URLs without reducing the count — the API refilled the list rather
than returning a short page. This is not a `lite` cache penalty: `instant`
with the same requests showed the same churn (0.904 for `highlights`, 0.701
for `text`).

### 7.4 Latency and cost

Median end-to-end latency over 36 samples per class/type (two passes, single
egress, directional only):

| Class | `lite` | `instant` | `fast` | `auto` |
|---|---:|---:|---:|---:|
| news | 834 ms | 748 ms | 828 ms | 752 ms |
| academic | 796 ms | 864 ms | 764 ms | 788 ms |
| Chinese | 856 ms | 856 ms | 850 ms | 817 ms |

The passes returned identical URLs but their medians moved in both directions
(news `instant` 872 → 722 ms, academic `instant` 1,127 → 838 ms, news `lite`
799 → 858 ms), so read these as directional; the table is the combined
36-sample median. Every plain call (18 queries × 4 types)
returned eight results and billed the flat up-to-10 price:
`costDollars.total` 0.004 for `lite` and `instant`, 0.007 for `fast` and
`auto`. No type was consistently faster; the spread is within run-to-run
movement.

### 7.5 Overlap and the documented `lite` rejections

Mean Jaccard against `lite`: `fast` 0.988, `auto` 0.988, `instant` 0.199.
`lite` runs the same search family as `fast` (as the docs say) and, in this
run, `auto` resolved to the same set; `instant` is a different index.

Both documented `lite` rejections returned HTTP 400 and named the field:

- `outputSchema`: `Invalid request body | Not supported with type "lite":
  outputSchema. Use type "auto" for other parameters.` (`INVALID_REQUEST_BODY`)
- `contents.summary`: `Invalid request body | Not supported with type "lite":
  contents.summary. Use type "auto" for other parameters.`
  (`INVALID_REQUEST_BODY`)

### 7.6 Tavily `include_published_date`

Six news queries at `topic: general`, `search_depth: basic`, eight results:

| Setting | Dated results |
|---|---:|
| `include_published_date: true` | 39/48 (81%; per query 7, 8, 8, 4, 8, 4) |
| flag omitted | 0/16 |
| `topic: news` (flag omitted, auto-enabled) | 3/3 first pass; 2/3 second |

The flag is opt-in and works on general search, not only `topic: news`; the
default shape still returns no dates. A raw-response spot check confirms the
field is `published_date` and carries an RFC 2822 string (for example `Fri, 14
Mar 2025 12:00:00 GMT`); the collector normalizes it to `YYYY-MM-DD`. Each
call billed one credit; median latency 2.2–4.1 s on this egress.

### 7.7 Per-class decision

Rule used: blind relevance/authority decides; a difference is "noise" when
the paired 95% bootstrap interval includes zero and |Δ| < 0.2 points on the
0–3 scale. Then cost (lite = instant < auto = fast), then forward
compatibility (lite is recommended, instant/fast legacy). Two vetoes: `lite`
loses if it returns >20% fewer results than `instant` when contents are
requested, or if its date coverage is clearly worse. "Clearly worse" here
means the paired interval excludes zero **and** `lite` has more than 20%
fewer dated results than `instant`, reusing the same 20% threshold.

| Class | Default | Basis |
|---|---|---|
| Current events | `lite` + `startPublishedDate` = start of the window | Quality tie (Δ relevance +0.10, interval crosses zero); same price as `instant`, and forward compatibility favors the recommended type; `lite` has 14% fewer dated results than `instant` (below the veto) and the 7-day window restored 8/8 dated results. |
| Academic | `instant` (use `lite` only when dates do not matter) | Quality tie (Δ relevance +0.02, +0.03 authority); same price; `lite` dated 29.2% vs 52.1% — 44% fewer dated results than `instant`, veto tripped. `auto` costs 75% more and still tracks `lite` (31.2%). |
| Chinese | `instant` (use `lite` only when dates do not matter) | Quality tie (Δ relevance +0.07, authority −0.10); same price; `lite` dated 52.1% vs 77.1% — 32% fewer dated results than `instant`, veto tripped. `auto` costs 75% more and still tracks `lite`. |

`auto` is not a quality upgrade in this run: it matched `lite`/`fast` and
billed 0.007. Use it only for parameters `lite` rejects (`contents.summary`,
`outputSchema`, `maxAgeHours`). `fast` matched `lite` at 0.007 and is legacy;
never choose it for cost or quality.

Caveats: six queries per class, one egress, one account, and a small judge
model; scores are title/URL/date judgments, not page-content verification.
The date veto is sensitive to how "clearly worse" is defined — the raw gaps
are in §7.2, and the academic/Chinese conclusions flip to `lite` if the date
difference is treated as metadata rather than a quality loss.


## 8. Full re-benchmark and parameter sweep, 2026-11-18

Full live re-test from one local Windows workstation using spare test accounts
(free-tier plans for both providers). Artifacts were written outside the skill
repository under `tavily-exa-router-workspace/bench-2026-11-18/`.

Blind quality scoring ran across 39 unique queries and 825 unique deduplicated
results (`batch_compare`, `lite_quality`, `mode_quality`, and
`comprehensive_modes` pooled and shuffled without provider or mode labels): 823
scoreable, 2 `unscoreable` (`empty_shell`), 0 login walls or injections in
search snippets. A stratified double-rating overlap of 164 items (8 queries,
19.9% of items) measured inter-rater agreement: relevance exact 89.63% / QWK
0.892, authority exact 87.80% / QWK 0.905, timeliness (n=89) exact 93.26% / QWK
0.951, zero `unscoreable` disagreements.

### 8.1 Broad 20-query comparison (`batch_compare.json`)

Tavily `basic` (`topic: "general"`) vs Exa `lite` (8 requested results per
query, 160 vs 160 returned):

| Metric | Tavily `basic` | Exa `lite` |
|---|---:|---:|
| Results returned | 160 | 160 |
| Allowlisted community-domain hits | **17** | 8 |
| Allowlisted authoritative-domain hits | 16 | **31** |
| Results carrying a publication date | 0 (flag omitted) | **88** |
| Median / p95 latency | 3,158 / 15,955 ms | **840 / 15,427 ms** |
| Blind relevance (0–3) | 2.459 | **2.650** |
| Blind authority (0–3) | 1.799 | **2.094** |
| Blind timeliness (0–3, 12 dated queries) | 1.874 | **2.250** |

Mean per-query domain Jaccard overlap was **0.151**. Paired blind differences
(Exa `lite` − Tavily `basic`): relevance **+0.189** `[+0.064, +0.318]`,
authority **+0.296** `[+0.146, +0.449]`, timeliness **+0.374**
`[+0.165, +0.571]`.

### 8.2 Exa `lite` vs legacy `instant` / `fast` / `auto` (`lite_quality.json`)

Six queries per class (`news`, `academic`, `chinese` — small sample, n=6 per
class), 3 latency repeats per query/type, plus contents/date-window/Tavily
checks:

| Class | Type | Dated share | Blind rel | Blind auth | Blind time | Median ms | Cost/call |
|---|---|---:|---:|---:|---:|---:|---:|
| news | `lite` | **76.1%** | 2.674 | 1.957 | **2.761** | 935 ms | $0.004 |
| news | `instant` | 68.8% | 2.417 | 2.188 | 2.000 | 1,068 ms | $0.004 |
| news | `fast` | 76.1% | 2.674 | 1.957 | 2.761 | 1,098 ms | $0.007 |
| news | `auto` | 76.1% | 2.609 | 2.043 | 2.761 | 1,172 ms | $0.007 |
| academic | `lite` | **56.2%** | 2.792 | 2.896 | — | **927 ms** | $0.004 |
| academic | `instant` | 52.1% | 2.750 | 2.938 | — | 1,556 ms | $0.004 |
| academic | `fast` | 56.2% | 2.750 | 2.896 | — | 1,003 ms | $0.007 |
| academic | `auto` | 43.8% | 2.812 | 2.875 | — | 1,404 ms | $0.007 |
| Chinese | `lite` | 54.2% | 2.583 | 1.917 | 2.104 | 1,114 ms | $0.004 |
| Chinese | `instant` | **79.2%** | **2.729** | 1.875 | **2.333** | 1,452 ms | $0.004 |
| Chinese | `fast` | 54.2% | 2.583 | 1.917 | 2.104 | 1,318 ms | $0.007 |
| Chinese | `auto` | 68.8% | 2.562 | 1.917 | 2.021 | 1,410 ms | $0.007 |

Key findings (`lite` − comparison, 95% paired CI):
- **News (`lite` holds):** `lite` led `instant` on dated share (76.1% vs 68.8%)
  and blind timeliness (+0.743 `[+0.389, +1.097]`).
- **Academic (flipped to `lite`; n=6 queries):** `lite` matched or exceeded
  `instant` on dated share (56.2% vs 52.1%), tied on blind relevance (+0.042
  `[-0.042, +0.146]`) and authority (−0.042 `[-0.146, +0.042]`), and ran faster
  (927 vs 1,556 ms). Academic queries now default to `lite`; dated product
  reviews (which previously borrowed `instant`'s cross-class date-coverage
  rationale without dedicated measurement) also revert to `lite`.
- **Chinese (`instant` holds when dates matter):** `instant` kept a large
  date-coverage lead (79.2% vs 54.2%) and higher blind relevance (`lite −
  instant` −0.146 `[-0.271, -0.042]`) and timeliness (−0.229 `[-0.396,
  -0.042]`).
- **Overlap and `auto`:** `lite` vs `fast` Jaccard was **0.975** (blind Δ
  0.000); `lite` vs `auto` Jaccard dropped to **0.615** (from 0.988 on
  2026-10-31), while blind quality differences remained within noise (all CIs
  crossing zero).
- **Contents, date windows, Tavily dates:** all 90 `contents` calls returned 8/8
  results (0% `lite` drop). `startPublishedDate` set to "now" collapsed
  academic recall to 1 result (dated `2026-11-21`, future-dated), while 7-day
  windows returned 7–8/8 dated results inside the window. `lite` +
  `outputSchema` and `lite` + `contents.summary` both returned 400 naming the
  field. Tavily `include_published_date: true` returned 43/48 dated results vs
  0/16 omitted vs 8/8 on `topic: news`.

### 8.3 Modes, serial latency, and community (`speed_test`, `mode_quality`, `comprehensive_modes`, `community_test`)

- **Serial latency (`speed_test.json`):** Round A medians (5 samples; 1 SSL EOF
  error on `exa_lite`): Exa `lite` **922 ms**, `auto` **953 ms**, `instant`
  **1,018 ms** vs Tavily `basic` **1,991 ms**. Round B medians (2 samples):
  Exa `lite` 838 ms, `auto` 977 ms, `fast` 1,286 ms, `instant` 1,647 ms,
  `deep-lite` 2,247 ms, `deep` 8,752 ms; Tavily `fast` 1,648 ms, `basic`
  1,936 ms, `ultra-fast` 2,197 ms, `advanced` 3,049 ms.
- **Mode blind scores:** in `mode_quality` (4 queries × 5 results = 20 per
  mode), Tavily `basic` (rel 2.65, auth 1.55) matched `advanced` (rel 2.60, auth
  1.50). In `comprehensive_modes` (4 queries × 8 results = 32 per mode), Tavily
  `ultra-fast` (rel 1.250, auth 0.906) and `fast` (rel 2.281, auth 1.000)
  trailed `basic` (rel 1.688, auth 1.562) and `advanced` (rel 2.469, auth
  1.562) on authority, while Exa `deep-reasoning` still drifted to English on
  the Chinese query (4/5 English titles).
- **`community_test.txt`:** EN Tailwind returned 2/8 allowlisted community hits
  on Tavily `basic`, 1/8 on Exa `lite`, 2/8 on Exa `deep`; CN Rust returned 1/8
  on Tavily `basic`, 3/8 on Exa `lite`, 1/8 on Exa `deep`.

### 8.4 Full parameter sweep (`param_sweep.json`, 136 probes) and 13-site matrix (`comprehensive_extract.json`)

- **Exa parameters:**
  - Omitting `type` defaulted to `auto` ($0.007). `lite` ($0.004), `instant`
    ($0.004), `auto`/`fast` ($0.007), `deep`/`deep-lite` ($0.012),
    `deep-reasoning` ($0.015), `numResults: 11` ($0.005), `100` (99 returned,
    $0.093), and `0`/`101` → 400 all held.
  - All 13 documented `lite`-incompatible fields (`outputSchema`,
    `contents.summary`, `maxAgeHours: -1`, `systemPrompt`, `stream`,
    `additionalQueries`, `extras`, `subpages`, `livecrawl`, `livecrawlTimeout`,
    `startCrawlDate`, `includeText`, `context`) returned HTTP 400 naming the
    field.
  - **`lite` + `snapshotAsOf`:** returned **HTTP 403 (`SNAPSHOT_NOT_ON_PLAN`)**
    on the free-tier account (paid plans only).
  - `company`/`people` + date → 400, `people` + `excludeDomains` → 400,
    `company` + `excludeDomains` → 200. `outputSchema` limits (11 props / 3
    levels / array missing `items` → 400; valid schema $0.007 with ~3 s extra
    latency). `highlights.dynamic` returned 400 without `Exa-Beta` header and
    200 with it.
  - Deprecated `type: "neural"` returned 200 at $0.004 and `"keyword"` at
    $0.007 with no warning; `startCrawlDate` and top-level `context` emitted
    `IGNORED_FIELD` warnings.
- **Tavily parameters:**
  - `include_answer` `basic` (918 chars) and `advanced` (672 chars) both billed
    1 credit. `auto_parameters: true` with explicit `search_depth: basic`
    billed 2 credits. `safe_search: true` returned 200 on `basic` and 400 on
    `fast`/`ultra-fast`. `include_domains_mode: prefer` allowed external
    domains (400 without `include_domains`); `filter_by_language` filtered
    strictly (400 without `language`).
  - **Undocumented server leniency (drift; keep documented limits):**
    `max_results: 21` returned 21 results (200); `chunks_per_source: 4`,
    `country` + `topic: news`, 1,501-char `query`, and `/extract` `timeout: 61`
    all returned 200 (`/extract` `timeout: 0` error cited `1 and 120 seconds`).
- **13-site fetch matrix (`comprehensive_extract.json` + `param_sweep.json`):**
  - Docs, Python docs, GitHub, HN, arXiv, dev.to, Medium succeeded on both.
  - **Tieba:** unavailable on both (Tavily failed; Exa `maxAgeHours: -1`
    returned `CONTENT_NOT_CACHED`, `24` and `0` returned `CRAWL_HTTP_403` rather
    than 500).
  - **Bilibili:** Tavily `basic`/`advanced` returned a 5,234-char login wall;
    Exa succeeded only at `maxAgeHours: 24` (460 chars; `-1` returned
    `CONTENT_NOT_CACHED`, `0` returned HTTP 412).
  - **X (`x.com/elonmusk`):** Tavily returned 5,094 chars of a login prompt
    shell; Exa returned `SOURCE_NOT_AVAILABLE`.
  - **Linux.do:** Exa succeeded across `-1`/`0`/`24`; Tavily `basic` failed and
    `advanced` succeeded with the tail prompt-injection block.
  - **Zhihu & Reddit:** Zhihu returned a login wall on both (Exa `0` returned
    `CRAWL_HTTP_403`); Reddit failed on both (`SOURCE_NOT_AVAILABLE` on Exa).
