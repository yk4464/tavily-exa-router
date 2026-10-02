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

## Contents

- §1 Broad 20-query comparison — volume, dates, latency, cost, domain overlap
- §2 Search-mode matrix — 10 modes × 4 fixed intents, plus manual review
- §3 Parameter and boundary matrix — 78 cases (Tavily, then Exa)
- §4 Known-URL retrieval matrix — 13 sites × both providers (2026-08-18)
- §4a Spot check, 2026-09-21 — 5 drift-prone sites re-run
- §4b Injection survey, 2026-09-25 — 11 pages × both providers, tail-append vs whole-body
- §5 Full re-run, 2026-10-03 — dual-network regression, drift findings, updated latencies

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

## 4b. Injection survey, 2026-09-25

Follow-up to §4's single Linux.do case, to test whether the phenomenon is
site-specific and how large a share of a response it can occupy. 11 public
pages × both providers = 22 fetches (Tavily `/extract` default; Exa
`/contents` with `text`), read-only, no login. 19 returned body text, 3
failed. Raw responses: `search_results/` on the run machine.

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
| Results carrying a publication date | 0 | **77–84** |
| Median latency (Local Windows) | 3,146 ms | 2,866 ms |
| Median latency (Aliyun Hong Kong) | **644 ms** | **2,040 ms** |
| Observed cost per query | 1 credit | $0.007 |

Average per-query domain Jaccard overlap dropped to **0.12** (identical across
both network endpoints; down from 0.22 in the 2026-08-18 baseline). The two
indexes remain sharply differentiated and complementary.

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

**Conclusion**: The core routing conclusions remain fully valid: community
queries route to Tavily, official documentation and dated queries route to Exa,
and all known boundary pitfalls persist. Latency figures are highly network-sensitive,
while Exa `deep` slowdown represents genuine vendor-side drift.
