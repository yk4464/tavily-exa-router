# Changelog

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
