# tavily-exa-router

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

English | [简体中文](README_zh.md)

Independent project. Not affiliated with, endorsed by, or sponsored by Tavily
or Exa Labs. Both names are trademarks of their respective owners.

An agent skill that teaches AI coding assistants **which web search API to
use — Tavily or Exa — for any given query**, and how to configure it. Routing
rules come from head-to-head API testing plus ~40 cited community sources
(August 2026) — see [`references/evidence.md`](references/evidence.md).

## Why

Tavily and Exa overlap far less than people assume (~22% per-query result
overlap, domain Jaccard, 20-query test). They are complements with clean
divisions of labor:

| Strength | Tavily | Exa |
|---|---|---|
| Community/forum content (Reddit, HN, Quora) | **strong** | weak |
| Primary/official sources & announcements | weak | **strong** |
| Academic content | partial | **strong** (arxiv-heavy) |
| Non-English (e.g. Chinese) quality | mixed | **strong** |
| Publish dates on results | ~never | **~52% of results** |
| Relevance score on results | **always** | never |
| LLM answer without reading links | **built-in** | via `outputSchema` |
| Structured JSON output | — | **built-in** |
| Fetching a known URL | **`/extract` works** | essentially can't |
| Basic query cost | ~$0.008 | ~$0.007 |

The skill encodes this into a 10-second routing table, mode-selection rules
(including which "fast" modes to avoid — they measured *worse*), parameter
recipes, and a pitfalls list (deprecated params, the `category=company` +
date-filter 400, content billing quirks).

Use it when you want a small, inspectable router whose recommendations tie
to dated, reproducible measurements rather than provider folklore. It is a
routing heuristic, not a universal search-quality benchmark: it routes
one-off public-web retrieval and explicitly declines monitoring jobs,
private-source search, URL-safety verdicts, and live-price lookups.

## Install

1. Get API keys — [Tavily](https://app.tavily.com) (free: 1,000
   credits/month) and [Exa](https://dashboard.exa.ai) (free: $20 signup
   credit + $10/month) — and export them (the skill reads these variables):

   ```bash
   export TAVILY_API_KEY=tvly-...
   export EXA_API_KEY=...
   ```

2. Install the skill into your runtime's skills directory:

   | Runtime | Command |
   |---|---|
   | Claude Code | `git clone https://github.com/yk4464/tavily-exa-router.git ~/.claude/skills/tavily-exa-router` |
   | Codex | `git clone https://github.com/yk4464/tavily-exa-router.git ~/.codex/skills/tavily-exa-router` |
   | Gemini CLI | `gemini skills install https://github.com/yk4464/tavily-exa-router.git` |
   | Others | Copy the folder into your tool's skills directory (many also read `~/.agents/skills/`) |

   On Windows, the same folders live under `%USERPROFILE%\.claude\skills\` etc.
   Restart the agent afterwards. Paths verified 2026-08 — if your runtime
   differs, check its skills documentation.

No commands to memorize: once installed, the skill loads automatically
whenever your agent needs a web search and the API keys are set.

Note: both dashboards and APIs may be unreachable from some networks
(mainland China typically requires a proxy — see
[community feedback](references/community-feedback.md)). Prices, quotas,
free credits, and product behavior are time-sensitive snapshots verified
2026-08 — check the vendor's current pages before budgeting production
traffic.

## What the agent gets

`SKILL.md` loads when a web search is needed and gives the agent:

1. **Routing table** — 13 task types → service + exact parameters
2. **Mode rules** — Tavily `basic`/`advanced` (never `fast`); Exa `auto`
   (when `deep-lite` is worth it)
3. **Fetching guidance** — Tavily `/extract` for known URLs, including which
   site types block it
4. **Second-opinion pattern** — how to merge both services' results with
   dedupe
5. **Pitfalls** — 7 gotchas (measured or verified against vendor docs)

Deep parameter tables and recipes live in `references/` and load on demand.

## Repository layout

```
tavily-exa-router/
├── SKILL.md              # the skill itself (routing rules)
├── README.md
├── MAINTENANCE.md        # how to re-test, refresh evidence, and version
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE               # MIT
├── tests/                # evidence regeneration kit (stdlib-only Python)
│   ├── README.md         # what each script measures + cost per run
│   ├── smoke_test.py     # cheap drift check (~$0.03) used by CI
│   └── *.py              # the batch/mode/feature/speed/extract tests
├── .github/workflows/    # monthly drift-check CI (enable via secrets)
└── references/
    ├── tavily.md         # full Tavily params, endpoints, recipes, pricing
    ├── exa.md            # full Exa params, contents options, outputSchema, pricing
    ├── evidence.md       # measured data behind every rule
    └── community-feedback.md  # ~40 cited community opinions (HN, Reddit, linux.do)
```

## Maintenance & updates

Evidence decays (prices rise, sites change their anti-bot posture, params get
deprecated), so the repo ships its own test kit: every number in
`references/evidence.md` can be regenerated by running the scripts in
`tests/`. A monthly GitHub Actions drift check flags when a documented fact
no longer holds. Cadence, refresh procedure, and semver rules live in
[`MAINTENANCE.md`](MAINTENANCE.md).

## Credits

Routing rules derived from head-to-head API testing (quality, latency, modes,
features, anti-block fetching, cost), plus community feedback from HN, Reddit,
and Chinese dev forums. Test date: 2026-08-17.

## License

[MIT](LICENSE)
