# Changelog

## Unreleased

Corrections from a multi-model audit with live API verification on
2026-10-06 (11 parallel review tracks: DeepSeek, GLM, Gemini, Tavily
official docs, Exa official docs, evidence-decay audit, and three
review passes). Every item below was re-tested against the live APIs.
Superseded numbers were overwritten rather than accumulated — the
previous values are recoverable from git history.

Behaviour fixes (these changed what the skill told the agent to do):

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
- **Community passes are conditional.** Interface/definition questions
  that the primary source already answers no longer force extra searches.
- **`startPublishedDate` is a window start, not "now".** A lower bound of
  the current instant excluded same-day official announcements.
- **Finance scope clarified.** A current quote is out of scope; news,
  filings and sector commentary route to `topic: "finance"`.
- **`400` is permanent.** Added to the retry rules — never retry it.

Price and parameter corrections (measured 2026-10-06):

- Exa `instant` is **USD 0.004/1k**, not 0.007 (three live requests). The
  documented price was 1.75× the real one.
- Exa `fast` was missing from the mode table entirely; added at USD 0.007.
- Exa bills **each result beyond 10** at USD 0.001: `numResults` 50 cost
  0.047 (6.7×) and 100 returned 99 for 0.096 (13.7×). The "widen
  `numResults` to 100" recommendation now quotes the real figure.
- Tavily `safe_search` is **available on all plans** since 2026-08 (was
  documented as enterprise-only), but is **rejected with `fast` /
  `ultra-fast`** — a combination that was missing from the rules.
- Tavily `max_results` default is unreliable: vendor pages disagree (5 vs
  10) and this account returned 10 when unset, so it must be explicit.
- `resolvedSearchType` is not a stable contract — the current spec marks
  it deprecated and possibly empty; observed as `""` in every response.
- `company` + `excludeDomains` returned **200** on 2026-08-18, 2026-10-03
  and 2026-10-06. The text said 400. Kept as unsupported because the
  official spec says so; the 200 is drift, not a contract.
- The 2026-03 price-rise date could not be confirmed against a vendor
  changelog entry (third parties split March vs April); now marked
  uncertain rather than stated flatly.

Evidence corrections:

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
- Bilibili is documented as succeeding in all three `maxAgeHours` modes
  on 2026-10-03 (forced-live included) instead of "across all modes".
- Latency and hit-count figures replaced with the 2026-10-03 re-run
  (`advanced` 14–15 vs `basic` 15, upper bound 4.9s).

Script fixes:

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
