# Changelog

## 1.5.0 — 2026-10-31

`SKILL.md` reworked (358 → 273 lines) around a new measurement of Exa's
`lite` type, and this release also publishes the 2026-10-06 multi-model audit
that had been pending in this changelog. The 2026-10-31 run is in
`references/evidence.md` §7, the 2026-10-06 observations in §6. Routing is
now a 14-item list instead of a table (mode selection keeps its short
tables), and every rule from the previous version has a recorded
destination.

### `SKILL.md` is rule-only now

`SKILL.md` is the product an agent reads end to end, so this release moved
everything only a maintainer needs out of it:

- **All dates are gone**, including the frontmatter
  `metadata.evidence-tested` field, the price-change date, and the dated
  notes on Bilibili, latency and the parameter snapshot.
- **Every `references/…` path and `§n` anchor is gone**, and the
  `References` section with them. The one-line Tavily options index now says
  what each option does instead of pointing at `references/tavily.md`.
- **Measurement numbers that existed only to justify a rule are gone** — the
  latency medians, the date-coverage percentages, the `score` values, the
  per-result cost multiples, the allowlist hit counts, the fetch-matrix
  tallies. The rules they supported stay. Figures that change what the agent
  sends — prices, the Tavily 20 / Exa 100 caps, `outputSchema` limits — stay.
- **Defensive wording is replaced by the instruction it was hedging**
  ("exhaustive coverage is not promised", "a clean JSON parse proves shape,
  not grounding", "a successful fetch proves nothing about safety", and the
  like).
- **The `Failure fallback` and `Never` sections are deleted**, after moving
  their unique rules into the body: deprecated Exa parameters are never sent,
  429 is not burst-retried, 401/403 switches provider instead of reusing a
  credential. Every other item already had a body rule. Only two rules were
  dropped rather than moved: the ~2 s wait before the single 5xx retry, and
  the 60 s ceiling on `Retry-After`. Both providers still switch on a failed
  call, so the routing and cost of a failure are unchanged.
- **The evidence did not move**: `references/evidence.md` §1–§7 keep every
  date, number and source, and this changelog keeps the reasoning. Deleting
  the `Never` and `Failure fallback` sections is why the 2026-10-06 items
  below that name `Never N` refer to a section that no longer exists.

`tests/validate_repo.py` now enforces the split: `SKILL.md` fails if it
contains `references/`, a `§` anchor or a `YYYY-MM-DD` date (frontmatter
included), `MAINTENANCE.md` / `CONTRIBUTING.md` / `tests/README.md` count as
documents when checking that every `references/*.md` file is linked from
somewhere, and the `§` anchor check runs over every document that cites one
instead of `SKILL.md` alone.

### Exa type defaults, decided by the 2026-10-31 measurement

Eighteen queries (six current-events, six academic, six Chinese) went through
`lite`, `instant`, `fast` and `auto`; quality was judged blind on 158 unique
query/URL pairs.

- **`lite` is the new default type** (`auto` was). Blind relevance and
  authority stay inside the noise band across the four types (paired 95%
  intervals cross zero, every |Δ| < 0.2 points on the 0–3 scale), and
  `lite`/`fast`/`auto` returned nearly identical URL sets (Jaccard 0.988).
  `lite` costs USD 0.004 and is the type the vendor recommends, so it wins on
  price and forward compatibility.
- **Current events → `lite` + `startPublishedDate`** at the start of the
  user's window. The date veto did not trip: `lite` was 14% behind `instant`
  on dated results, and a 7-day window restored 8/8 dated results with none
  before the bound. A bound set to the request instant still works, but
  collapses recall to 5–6 results, all same-day or future-dated.
- **Academic and Chinese → `instant`** (legacy). `lite` was 44% behind on
  dated academic results (29.2% vs 52.1%) and 32% behind on Chinese (52.1% vs
  77.1%), both past the 20% veto; `auto` costs 75% more and still tracks
  `lite`. Quality was a tie, so this is a date-coverage call, not a
  "newer is better" one. If `instant` is rejected or retired, fall back to
  `lite`.
- **Dated product reviews → `instant`**, on the same date-coverage basis;
  the review class itself was not measured separately.
- **`auto` is only for parameters `lite` rejects** (`outputSchema`,
  `contents.summary`, `maxAgeHours`) — not a quality or speed upgrade.
- **`lite` latency is taken from the run** (~0.75–0.86 s medians across all
  four types, direction flipping between passes), not the vendor's ~450 ms
  claim.
- **Low latency → Exa `lite`/`instant`.** The old "interactive speed →
  Tavily" tie-breaker was reversed: `instant` beat Tavily `basic` in all four
  2026-10-03 columns (969/3,603, 1,372/3,617, 1,114/2,353, 466/640 ms), and
  `auto` is not a speed tool.

### Trigger description rewritten and trigger-tested

- The frontmatter `description` was rewritten (1016 → 967 characters) to name
  the default entry point, the "do not probe" rule, and that naming
  Tavily/Exa is not a bypass. Tested in isolation: 20 prompts (10 should-load,
  10 should-not) × 5 trials × 2 versions = 200 replies, with only the
  description differing between versions. Holdout accuracy 0.875 → 1.00,
  should-load recall 0.90 → 1.00, should-not specificity 1.00 → 1.00,
  `regressions: []`. The one measurable difference is the positive case that
  names Exa: the old "skip only when the user explicitly names another tool
  or method" read that as a skip and fired 1/5 runs; the new "(not
  Tavily/Exa)" parenthetical fires 5/5. That supports "the named-provider
  ambiguity is fixed without regressions", not "triggering is better in
  general" — one model, a simulated host, 5 trials per prompt.

### Behaviour changes in `SKILL.md`

- **Entry is a four-step flow**: gate → route → state → call. Four scope
  gates each carry an exit, so a failed gate stops the request with a reason
  and spends no provider call. The decision is stated once before the first
  call (provider, strongest signal, fallback) and repeated only on a provider
  switch — never credentials or headers.
- **Scope excludes retrieval products**: multi-step research (Tavily
  `/research`, Exa Agent) and answer-only endpoints (Exa `/answer`) belong to
  the vendor's own product, not this skill.
- **Failure is no longer a bypass.** The old second bypass ("provider missing
  or blocked → configure the other one") is gone. A call-time failure stays
  in the skill: 5xx/timeout retries once, then switches provider; 429 is
  never burst-retried; 400 is permanent (fix or drop the constraint, never
  resend the same body — the rule moved out of the `Never` list, which this
  release deletes); 401/403 and an unconfigured provider both switch
  providers without installing anything mid-task; only when both providers
  fail does the host's built-in retrieval take over, with the failed
  attempts named. The retry delay and the `Retry-After` ceiling did not
  survive the rule-only pass (see above).
- **The community row's direction was wrong and is corrected**: Tavily leads
  community recall (16 vs Exa 6–7 allowlisted hits), and the Exa cross-check
  moved from `deep-reasoning` to `deep`.
- **`company` + `excludeDomains` is allowed** (see the correction below);
  `company`/`people` still reject date filters and `people` still rejects
  `excludeDomains`.
- **Tavily dates are opt-in.** `include_published_date` is beta and automatic
  for `topic: news`, `null` when no date is detectable; the new
  `filter_by_published_date` drops undated and out-of-window results and
  enables it. Measured 2026-10-31: 39/48 dated with the flag on a general
  search, 0/16 without it.
- **The Exa type table was reorganised** to `lite`/`instant`/`auto`/`deep`/
  `deep-lite`, with `fast` and `deep-reasoning` in a legacy note (`fast`'s
  lower bound is ~0.6 s, not ~1.2 s; `deep-lite` is never an upgrade).
- **`outputSchema` limits are written down**: 10 properties, 2 nesting
  levels, `items` on every array, 400 above that or on `lite`.
- **The `lite` supported set is written down** — `numResults`, dates, domain
  filters, category, `contents.text`/`highlights`, `snapshotAsOf` — together
  with the fields that return 400 and point at `auto`.
- **Over-limit result counts return the cap and say so**; the per-result
  surcharge is stated as its documented price, without the derived multiples.
  The measured 6.7×/13.7× at the `auto` base are in `references/evidence.md`
  §6; ≈11×/23.25× at the `lite` base is arithmetic on the documented price
  and lives here, not in a measurement.
- **Bilibili retrieval corrected**: cache mode (`maxAgeHours` `-1`/`24`)
  worked on 2026-10-03; forced live is flaky and last worked on 2026-08-18.
- **Merge metadata keeps Tavily `published_date`** when the caller enabled it.
- **Tavily's newer options get a one-line index** (`max_age_hours`,
  `include_domains_mode`, `language`/`filter_by_language`,
  `chunks_per_source`) stating what each one does — the parameter detail
  stays in `references/tavily.md`; the date parameters stay spelled out in
  the body because they change routing.
- **The `References` section is gone** with the rule-only pass above, so
  `references/` now serves maintainers only; `evidence.md` gained §7 and
  `MAINTENANCE.md` carries the map of which file holds what.
- **The Exa price-history date is resolved**: the search price update is the
  2026-03-03 "Exa Pricing Update" (`lite`/`instant` stay at USD 4/1k).

### 2026-10-06 audit (released with this version)

Corrections from a multi-model audit with live API verification on
2026-10-06 (11 parallel review tracks: DeepSeek, GLM, Gemini, Tavily
official docs, Exa official docs, evidence-decay audit, and three
review passes). Measurable items were re-tested against the live APIs;
wording-only items (e.g. `Never 9`, `outputSchema` grounding, 400 handling)
have nothing to measure. `Never N` names the section this release deletes;
the surviving rule lives in the body.
The 2026-10-06 observations are collected in `references/evidence.md` §6;
dated earlier records are kept as written, with dated corrections appended.

#### Behaviour fixes (these changed what the skill told the agent to do)

- **Dedupe no longer destroys evidence.** `dedupe by domain+path` collapsed
  8 distinct Hacker News discussions into 1, because HN threads differ only
  by `?id=`. Now keyed on the full URL including content-identifying query
  parameters; only known tracking params (`utm_*`, `ref`, `fbclid`) are
  stripped.
- **Tavily `score` is triage, not a filter.** `drop results under ~0.3` is
  gone. A search for one specific discussion returned that discussion at
  ~0.06, so the rule deleted the exact material the user asked for. Low
  scores are now kept for exact URLs, user-named domains, and rare topics.
- **`include_answer: "advanced"` is not a paid upgrade.** It was described
  as costing "extra latency and credit"; measured 1 credit, same as
  `basic`, and it is not reliably longer. (Measured 2026-10-06.)
- **Untrusted-content scope widened.** The rule covered "fetched pages",
  but a plain Tavily *search* returned the injection inside
  `results[].content` snippets at `score` ≈ 0.81 with no fetch call at all.
  The rule is now a standalone section covering page bodies, search
  snippets, titles, and server-side syntheses (`answer`, `summary`,
  `outputSchema`, `highlights`). Neither vendor documents injection
  filtering for these fields. Reporting is now neutral by default instead
  of `surface it to the user`, which risked reciting the payload.
- **`outputSchema` returns well-formed, not trustworthy.** "clean JSON"
  implied grounded content; well-formed ≠ verified, so the row now says to
  check fields against the cited pages.
- **`Never 9` yields to an explicit user request.** It previously read as
  an absolute ban on browsers, contradicting the bypass rule and eval 13.
  (That list is gone in this release; the rule now sits in the entry flow.)
- **Community passes are conditional.** Interface/definition questions
  that the primary source already answers no longer force extra searches.
- **`startPublishedDate` is a window start, not "now".** A lower bound of
  the current instant excluded same-day official announcements.
- **Finance scope clarified.** A current quote is out of scope; news,
  filings and sector commentary route to `topic: "finance"`.
- **`400` is permanent.** Added to the retry rules — never retry it.

#### Price and parameter corrections (measured 2026-10-06)

- Exa `instant` is **USD 0.004/1k**, not 0.007 (three live requests). The
  documented price was 1.75× the real one.
- Exa `fast` was missing from the mode table entirely; added at USD 0.007.
  (1.5.0 later moved it into the legacy note: same results as `lite`, more
  money.)
- Exa bills **each result beyond 10** at USD 0.001: `numResults` 50 cost
  0.047 (6.7×) and 100 returned 99 for 0.096 (13.7×). The "widen
  `numResults` to 100" recommendation now quotes the real figure. 1.5.0
  states the surcharge without multiples; its `lite`-base figures
  (≈11×/23.25×) are arithmetic on the documented price and live in this
  changelog, not in `SKILL.md`.
- Tavily `safe_search` is **available on all plans** since 2026-08 (was
  documented as enterprise-only), but is **rejected with `fast` /
  `ultra-fast`** — a combination that was missing from the rules.
- Tavily `max_results` default is unreliable: vendor pages disagree (5 vs
  10) and this account returned 10 when unset, so it must be explicit.
- `resolvedSearchType` is not a stable contract — the current spec marks
  it deprecated and possibly empty; observed as `""` in every response.
- `company` + `excludeDomains` returned **200** on 2026-08-18, 2026-10-03
  and 2026-10-06 while the text said 400. The current contract allows the
  pair — dates are forbidden for `company` and `people`, and
  `excludeDomains` only for `people` — so the 200 is compliant, not drift.
  1.5.0 corrects `SKILL.md`, both READMEs and the references to match.
- Exa's 2026-03 search-price rise is now dated: the 2026-03-03 "Exa Pricing
  Update" took search from USD 5/1k to USD 7/1k, with `lite`/`instant` at
  USD 4/1k. The earlier "third parties split March vs April" caveat is
  resolved against the vendor changelog.

#### Evidence corrections

- `references/evidence.md` claimed `numResults: 101` and
  `additionalQueries: 11` "were accepted"; the stored raw results record
  **400** for both. Corrected.
- `evidence.md` claimed `neural` / `keyword` / `livecrawl` were "silently
  ignored". Only the crawl-date and `context` pairs had controls;
  `neural` and `keyword` return 200 with different results and different
  billing. Deprecated ≠ inert.
- **The "Tavily 0 of 158 results carry `published_date`" statistic was an
  artifact of the collector**: `batch_compare.py` stored a literal `None`
  for Tavily's date field while reading Exa's real `publishedDate`. The
  script now reads the field; the figure is restated as soft evidence
  that cannot prove the API returns none.
- Bilibili was documented as succeeding in all three `maxAgeHours` modes on
  2026-10-03, forced-live included. The rule now says what the records show:
  cache mode (`-1`/`24`) succeeded, forced live is flaky and last worked on
  2026-08-18.
- Latency and hit-count figures replaced with the 2026-10-03 re-run
  (`advanced` 14–15 vs `basic` 15, upper bound 4.9s).

#### Script fixes

- `comprehensive_benchmark.py` crashed the **entire** benchmark on a legal
  HTTP-date `Retry-After`: `float()` raised `ValueError`, which is not an
  `HTTPError` subclass and so escaped the handler. Now parses
  delta-seconds and falls back to backoff for dates, NaN and negatives —
  the last two would make `time.sleep()` raise.
- `batch_compare.py` divided by zero when every query failed, losing the
  whole console summary exactly when diagnostics mattered; all aggregates
  now report `N/A` on empty input.
- `batch_compare.py` blindly retried permanent failures: 400/401/403 were
  each retried 3 times, waiting 12s to reach the same error the skill's
  own rules say to fix rather than retry.
- `validate_repo.py` missed API keys in JSON/YAML form and falsely flagged
  documentation placeholders like `EXA_API_KEY=your_exa_api_key_here`.
- `smoke_test.py` grew to 14 checks (~USD 0.062 + 4 credits): exact Exa
  prices for `auto`, `instant`, `deep`, `deep-lite`, `deep-reasoning` and the
  per-result surcharge above 10, replacing the `<= 0.02` guardrail that let a
  2.8× reprice pass; 1.5.0 added the `lite` price and the documented `lite` +
  `outputSchema` 400. 429/5xx/network errors are retried with `Retry-After`;
  infrastructure-only failures exit 2 instead of being reported as drift
  (exit 1). Each check is recorded once, with a fixed denominator. Missing
  keys still exit 0 but emit a `::warning::` annotation.
- `batch_compare.py` created no output directory and crashed after all paid
  calls; it now resolves `search_results/` from the script location and sends
  and records `topic: "general"` as its comment claimed.
- `mode_quality_test.py` no longer retries 400/401/403.
- `speed_test.py` round A survives individual failures and writes
  `search_results/speed_test.json`; `comprehensive_benchmark.py` writes
  partial results (marked `partial`) when interrupted.
- `comprehensive_benchmark.py` `near_duplicate_urls` counted exact duplicates
  as near-duplicates; it now counts same-source variants only. Earlier values
  in `evidence.md` §2 are annotated, not recomputed.
- All collectors exit with a clear message instead of a `KeyError` traceback
  when a key is missing.
- `validate_repo.py`: accepts every YAML scalar style for `description`;
  scans all git-publishable files (incl. `.sh` and extensionless) and bare
  `tvly-` keys; strips URLs before path-leak matching and labels paths by
  their real form; warns on non-empty `## Unreleased`; validates `name` by
  format and against `evals` instead of the directory name; checks README
  reference links, orphaned `references/*.md`, and `§` anchors per file.
- CI: `validate` job runs on every push and pull request without secrets;
  `smoke` stays on schedule/dispatch and annotates exit 1 (drift) vs 2
  (infrastructure). Workflow permissions reduced to `contents: read`.

#### Documentation fixes (from the same audit)

- README/README_EN aligned with `SKILL.md`: `startPublishedDate` is the window
  start, `score` is triage only, `outputSchema` is well-formed not grounded,
  Exa `instant` USD 0.004 and the missing `fast` row in the Chinese table,
  dated statistics, overlap no longer implies a better answer, the install
  prompt no longer sends test searches. New scope / data-flow / permissions
  section. FAQ 2 states the skill requires both providers: with one installed
  it does not apply; call-time failure of one provider falls back to the
  other.
- `references/evidence.md`: §5.3 restored to its 2026-10-03 text with a dated
  correction; new §6 for the 2026-10-06 targeted audit; artifact-not-retained
  notes for §4a/§4b; dated notes on Tavily date opt-in and Exa category rules.
- `references/exa.md`, `references/tavily.md`,
  `references/provider-api-audit-2026-08-18.md`: official-docs re-check
  2026-10-31 (not measured) — Exa `lite` and legacy `instant`/`fast`/
  `deep-reasoning` (2026-10-19), `company` + `excludeDomains` supported,
  `outputSchema` limits, `maxCharacters` up to 1,000,000, deprecated extras
  and `/search` subpages, free tier; Tavily `include_published_date`,
  `filter_by_published_date`, `max_age_hours`, `include_domains_mode`,
  `language`/`filter_by_language`, chunk defaults.
- `evals/evals.json`: 20 cases with descriptive `name`s; eval 1 no longer
  rewards a "now" lower bound; eval 12 no longer states tool availability in
  the prompt; new cases for 429, 401/403, snippet injection, full-URL dedupe,
  `numResults` cost, low-score exact URL, and 400.

### Documentation and tests in this release

- **Both READMEs re-synced to `SKILL.md` 1.5.0** (Skill-rule parity): the
  routing table now carries the new Exa type per row (current events `lite`,
  academic/Chinese/dated reviews `instant`, other Exa searches `lite`,
  `auto` only for `lite`-rejected parameters), the latency verdict points at
  Exa `lite`/`instant` instead of Tavily, the failure paragraph matches the
  rewritten fallback list (retry, then switch; 400 permanent; 401/403
  switch; both-failed built-in retrieval — the READMEs keep the retry
  timings that the rule-only `SKILL.md` no longer states), Scope lists the
  excluded retrieval products (Tavily `/research`, Exa `/answer`, Exa
  Agent), `company` + `excludeDomains` is described as allowed, Tavily dates
  as opt-in, and the per-result surcharge is stated with its base price.
  Version headers move to v1.5.0.
- **Entry wording follows the trigger test**: "configured for the session
  (tools, CLI, or API)" replaces "available in any form / configured API
  keys", and the READMEs' install section and first FAQ use the same
  phrasing, so availability is no longer read as "something may be
  reachable".
- **`tests/lite_quality_test.py` added** (~USD 1.68 + 9 credits): six
  queries per class × four types for count, date coverage, allowlist hits,
  latency, and `costDollars`, plus the contents-drop ratio, the
  `startPublishedDate` windows, the two documented `lite` 400s, and Tavily
  `include_published_date` coverage. Blind quality scoring stays outside the
  script so it can run on the stdlib only; the curated numbers are
  `references/evidence.md` §7.
- **`smoke_test.py` is now 14 checks** (~USD 0.062 + 4 credits), adding the
  `lite` price and the `lite` + `outputSchema` 400.
- **`MAINTENANCE.md`** names `lite_quality_test.py` in the quarterly re-test
  list, since Exa type defaults are now measured rather than asserted.
- **`evals/evals.json` is now 26 cases**: the six additions cover both
  providers failing into built-in retrieval, a named provider not being a
  bypass, structured JSON / summary forcing `auto`, Tavily's date opt-in,
  `company` + `excludeDomains` being allowed, and the research/answer
  products being out of scope. The seventh case tested a `Retry-After` above
  the 60 s cap and was dropped with that rule; case 14 covers 429 handling as
  the body states it.

## 1.4.0 — 2026-10-03


- New routing rule: for research or evaluative questions, run multiple
  searches and include a community-source pass — official docs state
  intended behavior while Linux.do/X/Reddit/HN threads surface actual
  behavior. SKILL.md gained a "Verifying a product/API/vendor claim"
  routing row (both providers) and the second-opinion section was
  broadened into "Multiple searches and second opinion".
- Documentation consistency patch across the repository:
  - Corrected drift-check count in `README.md` and `README_EN.md`:
    they stated "4 facts" while `smoke_test.py` runs 9 checks
    on a full pass (6 before v1.3.4, plus three pricing guardrails:
    Exa default search USD 0.007, Exa deep USD 0.012, Tavily advanced
    2 credits).
  - Refreshed evidence dates in README headers to reflect the 2026-08-18
    baseline alongside both rechecks (2026-09-21 spot recheck and 2026-09-25
    injection survey).
  - Completed root-level file listings in repository layout trees across both
    READMEs (`CONTRIBUTING.md`, `MAINTENANCE.md`, `CHANGELOG.md`, `LICENSE`).
  - Updated `tests/README.md` to detail all 9 smoke test checks and the
    pricing guardrails; documented `evals/evals.json` (13 routing/scope
    eval cases run via evaluation harness, not part of CI).
  - Added reader-facing sections to both READMEs: a usage example table
    (three routed requests with parameters and fallback) and a troubleshooting
    Q&A (skill not triggering, single-provider degradation, explicit user
    override, test-only API keys, updating via CLI or `git pull`).
  - Expanded `CONTRIBUTING.md` with a pre-submission checklist covering
    `validate_repo.py`, bilingual README parity, evidence/CHANGELOG
    discipline, four-point semver alignment, and the USD price rule.
  - Note: Scheduled drift-check CI on 2026-10-01 ran against remote `bea4992`
    (v1.3.1); v1.3.4–v1.4.0 had not run in automated CI at release time.
  - Prose polish across user-facing docs (both READMEs, `CONTRIBUTING.md`,
    `MAINTENANCE.md`, `tests/README.md`). `references/` is intentionally
    verbatim — its wording encodes measured caveats and claim boundaries.
- **Quarterly full regression run (2026-10-03)**:
  - Executed across two network environments (local Windows workstation and Aliyun Hong Kong cloud host), covering 172 test cases per endpoint (344 total calls) across modes, parameters, boundaries, and URL extraction, plus dedicated passes (`smoke_test.py` passing 9/9 on both endpoints, `speed_test`, and `community_test`).
  - Appended `references/evidence.md` §5 with dated snapshots; preserved all historical evidence sections §1–§4b unmodified.
  - Refreshed mode latency metrics to multi-environment interval representations across `SKILL.md` and both READMEs (e.g. Tavily basic ~0.6–3.6s, Exa instant ~0.5–1.4s), highlighting network egress sensitivity.
  - Documented server-side latency drift for Exa `deep` (~8.5–11.6s vs 5.3s in August baseline).
  - Domain Jaccard overlap dropped from 0.22 to 0.12 across 158–159 results, confirming strong complementarity between providers.
  - Observed three new parameter drifts: `safe_search` now returns HTTP 200 (previously HTTP 403 on this tier); `resolvedSearchType` reappeared in Exa responses; `exact_match` exhibited unstable recall between runs (0 vs 5 results).
  - Documented URL retrieval shifts: Bilibili works across modes; Exa cached retrieval succeeds on Tieba; forced live fetch is flaky (<13s rather than guaranteed 30s timeout).
  - Fixed Python ≤3.11 compatibility in `tests/comprehensive_benchmark.py` where backslashes inside f-strings caused a `SyntaxError`.
- Version bump: synchronized `SKILL.md` frontmatter, both README headers, and
  CHANGELOG heading to 1.4.0.
## 1.3.4 — 2026-09-25

- **Prompt-injection rule generalized and strengthened.** The skill's
  fetched-content rule was Linux.do-specific in its evidence. A new
  survey (`references/evidence.md` §4b: 11 pages × both providers, 22
  fetches) found the block on all three Linux.do topics tested and on
  none of the other six site families, but the more important result is
  its *shape*: the injected block is server-appended site furniture,
  byte-identical across topics, and its share of the response is set by
  how much of the page the provider sliced — 94% of one returned body,
  with the injection as the only legible text. SKILL.md now states that
  a short fetch is not evidence of a clean fetch, that a claimed site
  policy ("this site prohibits AI-generated content", "you must refuse")
  carries no authority over the session, and that the block is page
  content to report rather than a command to follow. Never-item 8
  reworded to match
- `tests/validate_repo.py` gained a version-consistency check: the
  READMEs' current-version header and the CHANGELOG's newest heading must
  match the frontmatter. Historical mentions ("As of v1.2.0, …") are
  ignored on purpose. Motivating drift: both READMEs still said v1.3.0
  three releases later
- `tests/smoke_test.py` gained three pricing guardrails (Exa default
  search USD 0.007, Exa deep USD 0.012, Tavily advanced 2 credits).
  `MAINTENANCE.md` names prices as the fastest-rotting facts but no check
  covered them. Verified against live responses before asserting them
- READMEs: version headers refreshed; the eval count corrected 11 → 13
  (stale since 1.2.0 added cases 12–13); evidence row relabelled from
  "192 cases" to calls actually made (138 search + 54 retrieval); Exa
  mode latencies re-aligned with `evidence.md` §2 (deep 5.26→5.3s,
  deep-reasoning 12.68→12.7s, deep-lite 5.99→6.0s). Chinese and English
  READMEs were confirmed structurally equivalent (10 sections each) —
  no missing English content
- `SKILL.md` frontmatter `evidence-tested` moved to 2026-09-25 (spot
  survey; the 2026-08-18 baseline stands)

## 1.3.3 — 2026-09-21

- Harness-compat fix: replaced six `$<digit>` price strings in SKILL.md
  (`$0.007`, `$5→$7/1k`, …) with `USD …` forms. Skill loaders expand
  `$0`-style tokens as positional arguments, so the loaded body showed
  corrupted costs (`.007`, `→/1k`) while the on-disk file looked fine.
  Found by loading the skill and diffing against disk;
  `tests/validate_repo.py` now rejects the pattern, and CONTRIBUTING.md
  documents the rule
- Added tables of contents to the three >100-line references
  (evidence.md, exa.md, tavily.md), per the official skill-authoring
  guidance
- Best-practices comparison (official authoring guide, anthropics/skills
  skill-creator, Linux.do #1424073, X practitioner guides): description
  length, <500-line body, one-level references, gotchas section, and
  script-backed checks already conform. The description stays imperative
  on purpose — that wording was trigger-tested 6/6; third-person
  restyling is rejected as regression risk without a new trigger run

## 1.3.2 — 2026-09-21

- Spot re-check of the five most drift-prone fetch targets
  (`references/evidence.md` §4a): Tavily Extract unchanged (Linux.do, X,
  Bilibili usable; Reddit still fails; the Linux.do prompt-injection tail
  persists). Exa Contents improved on Linux.do (live and 24h-cache now
  return usable text; the 2026-08-18 live timeout no longer holds) and
  regressed once on Bilibili forced-live while 24h-cache still worked —
  SKILL.md's known-URL matrix wording updated to match; routing
  conclusions unchanged
- Pricing re-verified against both vendors' public pricing pages: Exa
  ($7/1k search, $1/1k contents per type, $12–15/1k deep, free tier) and
  Tavily ($0.008/credit PAYG, 1,000 free credits/month) match the 2026-08
  snapshot; local smoke test 6/6 (Tavily basic still 1 credit, Exa auto
  still $0.007, company+date still HTTP 400)
- community-feedback.md: noted the 2026-09-07 independent reproduction of
  exa-mcp-server #396 and the proposed fix PR #430; all seven tracked
  provider issues remain open
- Frontmatter `evidence-tested` moved to 2026-09-21 (spot recheck; the
  full 2026-08-18 baseline stands)

## 1.3.1 — 2026-09-21

- Replaced inline "one-off measurement" caveats across SKILL.md, exa.md,
  and tavily.md with explicit dated pointers into `references/evidence.md`
  §1–§4; tightened assertions to match the evidence ("must not" for
  category+date/excludeDomains, "drift, not a contract" for boundary
  responses like `max_results: 21`, `maxAgeHours: 721`, 1,501-char queries)
- evidence.md: moved method limits to the opening paragraph; dropped the
  §5 conclusions list that duplicated SKILL.md's routing table
- Precision fixes: `evidence-tested` dated exactly (2026-08-18); repaired
  two lost newlines that glued a §3 heading and a JSON code fence to
  surrounding text; fixed a dangling §6 pointer left by the renumbering

## 1.3.0 — 2026-08-26

- Restructured SKILL.md into directive form: imperative rules, tables,
  and a consolidated 12-item "Never" list; removed persuasive prose
  (why-to-use arguments, benefit paragraphs, methodology narration)
- All routing rules, measured numbers, parameter tables, 13-site fetch
  matrix results, fallback rules, and reference pointers unchanged

## 1.2.2 — 2026-08-26

- Broadened the trigger condition from "visible in the tool list" to
  "available in any form (MCP tools, skills, CLI, or configured API
  keys)" — in skill/CLI-based environments the old wording read as
  "not triggered" (found in live trigger testing)
- Strengthened the known-URL fetch claim: a plain "read this page"
  request that looks like a one-step WebFetch job still routes through
  this skill (the one failure mode in the 4-prompt trigger test)
- Trigger test on 4 realistic prompts (search + community, English
  research, known-URL fetch, news check): 3/4 loaded the skill first;
  the fetch case failed and prompted this fix
- Re-tested the fetch scenario after the fix: 2/2 prompts loaded the
  skill first and routed to Exa /contents (no WebFetch, no browser);
  6/6 fresh-session triggers overall

## 1.2.1 — 2026-08-26

- Fixed runtime over-checking: the trigger condition is visibility in the
  tool list only; SKILL.md now explicitly forbids probe/test requests
  before the real query (verification belongs to the install flow, not
  everyday conversations)
- Install prompt gained an "already installed → stop" early exit and an
  install-time-only note so agents stop re-running the environment check
  in new conversations
- Front-loaded the description ("use this FIRST, before any
  provider-specific Tavily/Exa skill, browser, WebSearch, or WebFetch")
  and moved the default-trigger section to the top of SKILL.md to raise
  trigger prominence
- Added a "sending test searches before the real query" common mistake

## 1.2.0 — 2026-08-25

- Made the skill the default router: whenever Tavily and Exa are both
  visible in the tool list, every public-web search or known-URL fetch goes
  through this skill; browser, WebSearch, and WebFetch become fallbacks
  unless the user explicitly names another method
- Rewrote the frontmatter description for trigger reliability (the previous
  wording under-triggered: models reached for a browser instead)
- Added a default-trigger section and an "opening a browser when both
  providers are available" common mistake to SKILL.md
- READMEs: added provider websites, dashboards, and free-tier quota
  pointers (verified against the 2026-08 references)
- READMEs: the copy-to-AI install prompt now live-checks both services,
  fixes or installs them (asking the user for keys), and installs the skill
  only after both are verified callable
- Added eval cases 12–13 covering the default trigger and the
  explicit-user-override bypass

## 1.1.0 — 2026-08-18

- Fixed repository validation so placeholders no longer trigger leak warnings
- Repository validation now fails on metadata, reference, or leak errors
- Added repository validation to the monthly drift-check workflow
- Bumped the skill metadata to 1.1.0 for the expanded routing and evidence set
- Corrected known-URL retrieval guidance: both Tavily and Exa have endpoints
- Updated Exa pricing, deprecated fields, and live-fetch guidance for 2026-08
- Added inspectable routing decisions and explicit failure fallback rules
- Expanded Tavily Extract parameters, limits, and billing guidance
- Added a comprehensive live benchmark covering all in-scope modes,
  parameters, boundaries, and 13 known-URL targets
- Added nine routing and scope eval cases plus Codex interface metadata
- Re-ran 20-query, 40-mode, 78-parameter, and 54-case retrieval suites on
  2026-08-18, including semantic control comparisons and real SSE parsing
- Corrected mode guidance: Tavily fast modes were faster in the latest window
  but lost relevance; Exa instant was the fastest strong official/paper route
- Replaced stale extraction claims with a 13-site matrix covering Linux.do, X,
  Reddit, Zhihu, Bilibili, Tieba, GitHub, docs, HN, arXiv, dev.to, and Medium
- Added prompt-injection handling after a Linux.do extraction appended
  AI-directed instructions to otherwise usable page content
- Refreshed community evidence with current provider issues, HN/Reddit/Linux.do/
  V2EX reports, and explicit confidence and bias boundaries

## 1.0.2 — 2026-08-17

- Chinese README is now the primary `README.md`; English moved to `README_EN.md`

## 1.0.1 — 2026-08-17

- Added Chinese README (`README_zh.md`) with language switcher links

## 1.0.0 — 2026-08-17

Initial release.

- 10-second routing table (12 task types), mode-selection rules, parameter
  quick reference, fetch guidance, second-opinion dual-search pattern
- References: full Tavily/Exa parameter tables, measured evidence (2026-08
  testing), ~40-source community feedback
- Two pre-release review rounds applied: round 1 — install paths,
  placeholder, consistency and claim-strength fixes; round 2 — scope
  boundaries, fetch-endpoint nuance, routing conflict precedence, mode/claim
  calibration, quotation policy and disclaimers
