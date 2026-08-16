# Evidence — Measured Data Behind the Rules (2026-08-17)

All numbers below come from direct API testing against both services from one
machine (default settings unless noted). Directional, not statistically
exhaustive — re-verify before relying on fine numbers.

## 1. Result quality by query type (20 queries × 8 results each)

Category mix: factual, news, Chinese tech/news, long-tail troubleshooting,
niche technical, comparisons, entities, academic, community, how-to, misc,
product review.

| Metric | Tavily | Exa |
|---|---|---|
| Total results | 159 | 159 |
| Community-domain hits (Reddit/HN/SO/Zhihu/juejin/dev.to…) | **21** | 8 |
| Authoritative-domain hits (arxiv/gh.com/Reuters/official docs) | 6 | **21** |
| Results with publish date | 0 | **83 (~52%)** |
| Notable per-query gaps | mamba survey: 2/8 authoritative | mamba survey: **7/8 arxiv**; product review: 8/8 dated |

Chinese-language spot checks (separate round): Exa returned specific dated
events from official engineering blogs; Tavily returned undated roundup
listicles including content-farm pages.

Freshness spot check ("latest AI model releases"): Exa surfaced primary vendor
announcements (Google blog, x.ai, NVIDIA, Meta); Tavily surfaced only
aggregator/tracker sites.

### 1.1 Community-content round (2 queries, 8 results each)

- EN "tailwind css criticism real developer experience": Tavily 3/8 UGC
  platforms (HN, Reddit, dev.to); Exa auto 0/8 UGC but 5–6 personal-blog
  experience posts; Exa `category: "personal site"` 8/8 individual developer
  blogs, all on-topic opinion pieces.
- CN "Rust 生产环境使用经验 踩坑": Tavily 3/8 UGC (2 Chinese Reddit threads,
  Zhihu) but 2 off-topic fillers; Exa 1/8 UGC yet 7–8 on-topic experience
  articles from engineering blogs.

## 2. Index overlap

Per-query domain Jaccard similarity averaged **0.22** across 20 queries.
The two indexes are largely complementary — a second service adds sources, it
rarely duplicates. Caveat: low overlap alone does not prove a second call
improves the final answer — justify dual-search by task impact or weak first
results, not by this number.

## 3. Latency (median, interleaved runs)

| Scenario | Tavily | Exa |
|---|---|---|
| Default search, 5 results | ~800ms | ~670ms |
| Default search, 8 results | ~800ms | ~670–900ms |
| + full text extraction | 1297ms | **686ms** |
| Premium tier | advanced 1872ms | deep-lite 5373ms |
| Follow-up (n=1) | — | `deep` 5.1s at $0.012 |

Vendor guidance (not an SLA): Exa documents approximately ~4s for
`deep-lite`, 4–15s for `deep`, and 12–40s for `deep-reasoning` — see
https://exa.ai/docs/reference/pricing and
https://exa.ai/docs/reference/search-api-guide. Our `deep` figure above is
a single-run observation in one environment, not a latency benchmark; keep
each mode's evidence separate rather than merging them into a "deep modes"
range.
| "Fast" tiers | ultra-fast 892ms / fast 954ms | instant 807ms / fast 940ms |

"Fast"/"instant" labels did not beat the defaults in wall-clock time.

## 4. Mode quality (4 queries: research / technical / Chinese / factual)

- Tavily `fast`: same result repeated 4x on one query; Polymarket gambling
  pages on a CEO factual query; weak Chinese sources. Clear degradation.
- Tavily `advanced` (2 credits): better factual sources (NYT, Wikipedia over
  prediction-market spam), better Chinese picks. Modest, consistent.
- Exa `instant`: mostly fine, occasional off-topic hit.
- Exa `auto`: surfaced OpenAI/OWASP/Microsoft official docs first.
- Exa `deep-lite` ($0.012, 3.8–7.9s): no clear quality gain over `auto`;
  some generic marketing pages crept in.

## 5. Feature verification matrix

| Feature | Result |
|---|---|
| Tavily `include_answer` basic/advanced | works; concise vs detailed |
| Tavily `topic=news` + `time_range=week` | works; middling relevance on policy query |
| Tavily `include_domains: arxiv.org` | strict — 5/5 results arxiv |
| Tavily `exact_match: true` | **0 results returned** — unreliable |
| Tavily `country: germany` | no visible effect on result domains |
| Exa `outputSchema` | clean structured JSON (~+2s) |
| Exa `highlights` (with query) | on-topic snippets |
| Exa `summary` (with focus query) | good targeted summaries |
| Exa `subpages` + `subpageTarget: "pricing"` | **empty arrays** — unreliable |
| Exa `startPublishedDate` (7d window) | effective, all results in window |
| Exa `category: company` | works; noisy for generic queries |
| Exa `category: company` + `startPublishedDate` | **HTTP 400** (dedicated index) |
| Exa `includeDomains: ["*.substack.com"]` | strict — 5/5 substack |

## 6. URL fetching / anti-block (5 community sites)

| Site | Tavily `/extract` | Exa `/contents` forced-live |
|---|---|---|
| linux.do (Discourse forum) | full content, 30KB | nothing returned |
| x.com profile | real tweets w/ timestamps | nothing returned |
| zhihu.com | login-wall page (7.8KB nav) | login stub (152 chars) |
| bilibili video page | JS skeleton (465 chars) | nothing returned |
| tieba.baidu.com | hard failure | nothing returned |

## 7. Cost

| | Tavily | Exa |
|---|---|---|
| Basic query | 1 credit ≈ $0.008 | $0.007 (measured, stable) |
| Premium query | advanced $0.016 | deep-lite $0.012 |
| Free tier | 1,000 credits/month | $20 signup + $10/month |
| Contents | bundled | $1/1k pages per content type |

## 8. Community reputation summary

From ~40 sources (HN threads, Reddit r/Rag, linux.do, dev.to, vendor-neutral
and competitor-flagged posts; full quotes and links in
[`community-feedback.md`](community-feedback.md)):

**Tavily** — praised for all-in-one search+read+summarize (token-efficient,
popular default for coding agents), speed, and the generous 1,000
credits/month free tier. Complaints: hard 429 rate-limiting on the free tier
(sometimes surfacing as empty responses), 1k credits running out, and mixed
search-quality reports (notably from Chinese users, matching our Chinese
quality test). Some users report cached/dead links (competitor-sourced claim).

**Exa** — praised for semantic/exploratory search, "find similar" workflows,
full-text returns, and developer experience; a no-key MCP free tier circulates
in Chinese dev communities. Complaints: price raised $5→$7 per 1k searches
(2026-03) with a pricing table HN users call confusing; perceived accuracy on
simple factual queries ranked below Tavily by some; weak coverage of forums,
social media, and sparse pages (matches our 21-vs-8 community-domain result).

**Consensus that matches our measurements:** Tavily for day-to-day factual
queries and direct RAG; Exa for semantic exploration, deep research, and
freshness. Neither is strong on forum/social coverage — the community routes
those to dedicated providers; between these two, Tavily is the better pick.

## Method notes

- APIs called directly (no CLI overhead), default-ish params, 8 results.
- Latency interleaved to cancel network drift; medians of 3–5 runs.
- Quality judgments: domain-tier classification + manual review of titles/
  snippets; no blind scoring — treat qualitative rows as directional.
- Link spot-check (HTTP status) was inconclusive: most non-200s were
  anti-bot blocks against the test client (Britannica 403, etc.), not dead
  links. Not used for any rule.
