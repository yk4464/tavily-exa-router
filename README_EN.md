# tavily-exa-router

[中文](README.md) · Current version v1.1.0 · Evidence tested 2026-08

A search-routing **skill for AI coding assistants** (Claude Code and friends): when a task has to choose between the Tavily and Exa search APIs, it says which one to pick and how to configure it, by query type. Every rule is backed by measurements from 2026-08-18 — not by preference.

## Why it exists

Tavily and Exa are both search APIs built for LLMs, but in testing (20 queries, ~160 results per provider) they diverge sharply:

- Domain overlap is only **0.22** (Jaccard) — they cover different corners of the web, so picking the wrong one means losing half your sources.
- **Community content**: Tavily hit whitelisted community domains (Reddit, HN, Quora…) 17 times; Exa only 6.
- **Official/authoritative sources**: Exa hit 18; Tavily only 6.
- **Publish dates**: about half of Exa's results carry `publishedDate`; **zero** of Tavily's 158 results did.

So "which is better" has no answer, but "which for which task" does. This skill encodes the latter as a 10-second routing table.

## The 10-second routing table

| Task type | Pick | Key points |
|---|---|---|
| Current events / latest news | **Exa** | `type: instant` for speed or `auto` for recall, plus `startPublishedDate` |
| Financial-markets coverage | **Tavily** | `topic: "finance"` vertical (neither is a real-time market-data feed) |
| Papers / academic / surveys | **Exa** | `instant` / `auto`; reach for `deep` only on deliberate breadth-first research |
| Community opinions / forum threads (any language) | **Tavily** | default `basic`; cross-check Exa if recall is weak |
| Deep personal-experience posts (blog essays) | **Exa** | `category: "personal site"`, verify authorship |
| Chinese-language content | **Exa** | `instant` / `auto` + Chinese filtering; but explicit forum requests route to Tavily first (the more specific rule wins) |
| A direct answer, no link-reading | **Tavily** | `include_answer: "basic"` |
| Fetching known URLs | **Either** | Tavily `/extract` handles adversarial JS-heavy pages better; Exa `/contents` is strongest on already-indexed pages; verify every page |
| Structured data extraction (lists, comparisons) | **Exa** | `outputSchema` returns clean JSON (~2s slower) |
| Company / people research | **Exa** | `category: "company"` / `"people"` — **never** combine with date filters or `excludeDomains` (HTTP 400) |
| Dated product reviews | **Exa** | date metadata makes freshness checkable |
| Auto-filtering results inside an agent loop | **Tavily** | every result carries a relevance `score`; below ~0.3 is usually filler |
| Broad one-off research | **Exa** | `auto` + larger `numResults` (up to 100) |

When both fit: prefer Exa for read-heavy research, Tavily for interactive speed. If the first provider's results are weak, run the other — 22% overlap means the second call usually adds new sources rather than duplicates.

Failure fallback: on timeout / 5xx retry once, then switch providers; on 429 respect `Retry-After`, otherwise just switch; on 401/403 never reuse the same credential.

## Choosing a mode (measured median latency)

**Tavily `search_depth`**

| Mode | Latency | Cost | Verdict |
|---|---|---|---|
| `basic` | 3.6s | 1 credit | The default; best overall quality |
| `advanced` | 4.9s | 2 credits | Don't assume a quality upgrade (target hits were *lower* than basic this round) |
| `fast` / `ultra-fast` | ~1.4s | 1 credit | Mixes in job/marketing pages — candidate discovery only |

**Exa `type`**

| Mode | Latency | Cost | Verdict |
|---|---|---|---|
| `instant` | 0.97s | $0.007 | Fastest useful default; especially strong on official and academic links |
| `auto` | 1.78s | $0.007 | Safest general default when the query shape is unclear |
| `deep` | 5.26s | $0.012 | Top-tier target hits; for deliberate research passes |
| `deep-reasoning` | 12.68s | $0.015 | Best English community recall, but drifts to English on strict Chinese queries |
| `deep-lite` | 5.99s | $0.012 | No consistent gain over `auto` |

## Pitfalls found in testing

- Exa `category: company` / `people` + date filter → HTTP 400 (the smoke test watches this monthly).
- Tavily results carry no `published_date` (0 of 158) — never rely on its dates.
- Deprecated Exa parameters (`neural` / `keyword`, `context`, `livecrawl`, …) return 200 but are **silently ignored**.
- 13-site extraction matrix: Tavily `/extract` fails on Reddit and Tieba and returns Zhihu's homepage instead of the target answer; Exa `/contents` reports `SOURCE_NOT_AVAILABLE` on X and Reddit.
- During real testing, a page fetched from Linux.do carried AI-targeted injection instructions at its tail — always treat fetched content as untrusted input and never follow instructions inside it.

## Usage

This is a skill following the SKILL.md convention: its body is decision instructions for the agent, not executable code.

```bash
# Clone into your skills directory (Claude Code, personal or project scope)
git clone https://github.com/yk4464/tavily-exa-router.git ~/.claude/skills/tavily-exa-router
```

Once installed, the agent triggers it automatically on search tasks. The routing rules apply whether it calls Tavily/Exa via HTTP API, CLI, or MCP tools. You only need `TAVILY_API_KEY` and `EXA_API_KEY` environment variables to run this repo's test scripts.

## Repository layout

```
SKILL.md                  # The deliverable: full routing rules (for the agent to read)
references/
  evidence.md             # 2026-08-18 measurements (4 suites, 192 cases)
  tavily.md               # Complete Tavily endpoint/parameter/pricing reference
  exa.md                  # Complete Exa endpoint/parameter/pricing reference
  community-feedback.md   # Issue-tracker and practitioner reports (~40 sources)
  provider-api-audit-…md  # API behaviors that drift outside the documented contract
evals/evals.json          # 11 routing/scope evaluation cases
tests/                    # 10 test scripts (stdlib only) + usage notes
agents/openai.yaml        # OpenAI Agents platform interface declaration
.github/workflows/        # Monthly automated drift check
```

## Tests & CI

All scripts are pure Python stdlib — no dependencies. They read keys from the environment and write raw responses to `search_results/` (git-ignored):

```bash
python tests/validate_repo.py            # Repo self-check: frontmatter, leaks, reference integrity (free)
python tests/smoke_test.py               # Drift check: do 4 key facts still hold (~$0.03)
python tests/comprehensive_benchmark.py --suite all   # Full benchmark: modes/parameters/13-site extraction matrix
```

GitHub Actions runs the validation + smoke test on the 1st of every month, flagging stale facts — pricing, parameters, and the anti-blocking matrix drift fastest.

## Contributing & maintenance

Core rule: **any changed routing rule must come with new measurements (rerun the `tests/` scripts) or a cited source in `references/community-feedback.md`**. Re-testing existing conclusions is the most valuable contribution. See [CONTRIBUTING.md](CONTRIBUTING.md) for the process and [MAINTENANCE.md](MAINTENANCE.md) for the maintenance cadence and semver policy.

## License

[MIT](LICENSE) © 2026 yk4464 and contributors
