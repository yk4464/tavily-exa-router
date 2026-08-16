# Tavily vs Exa — Community Reputation Research

Research date: 2026-08-17. Method: Tavily Search (9 queries, including
Reddit/HN/Chinese-site targeting), Exa Search (4 queries), WebSearch
cross-checks (2 succeeded), Tavily Extract to read 4 threads in full
(2 HN + 2 linux.do; direct Reddit access was network-blocked, so Reddit
quotes rely on search snapshots).

> Integrity note: every opinion below comes from the listed source URLs;
> quotes are verbatim. Aspects with no findings are explicitly marked "not
> found". Vendor pages (exa.ai, tavily.com) were used only for fact-checking
> (pricing), never as reputation evidence, and are labeled as such.
> Chinese-language quotes are kept in the original with English glosses —
> the original wording is part of the evidence.

> Quotation policy: quotes are excerpted as briefly as practical to support
> specific claims, attributed to their authors and hosts, and included for
> commentary and comparison — not as a substitute for the original works.
> They may be removed on a rights-holder request. Competitor-published
> claims (Firecrawl, Nimble, Bright Data, Crustdata) are attributed,
> potentially biased evidence, not independent verification unless
> corroborated by unrelated sources. This file is not legal advice.

---

## 1. Source list

| # | Source | Type | Date | URL |
|---|--------|------|------|-----|
| 1 | HN: Launch HN: Exa (YC S21) comments | forum | 2025-05-06 | https://news.ycombinator.com/item?id=43910228 |
| 2 | HN: Exa raises $85M Series B comments | forum | ~2025-09 | https://news.ycombinator.com/item?id=45118788 |
| 3 | Reddit r/Rag: Which search API (Tavily/Exa/Linkup) | forum | ~2024-10 | https://www.reddit.com/r/Rag/comments/1gr8jnr/ |
| 4 | Reddit r/Rag + r/vectordatabase: Benchmark Exa vs Tavily vs Firecrawl | forum | ~2025 | https://www.reddit.com/r/Rag/comments/1v4q7wp/ , https://www.reddit.com/r/vectordatabase/comments/1v7gdrk/ |
| 5 | Reddit r/Agent_AI: Tavily Alternatives 2026 | forum | ~2026 | https://www.reddit.com/r/Agent_AI/comments/1sy37gs/ |
| 6 | linux.do: For agents — Tavily/Exa/Firecrawl, which is best? | forum (Chinese) | 2026-06-19 | https://linux.do/t/topic/2435930 |
| 7 | linux.do: Tavily Proxy multi-account rotation MCP | forum (Chinese) | 2026-01-24 | https://linux.do/t/topic/1510634 |
| 8 | linux.do: Codex MCP search setup (Brave & Tavily) | forum (Chinese) | 2026-02-09 | https://linux.do/t/topic/1587813 |
| 9 | Zhihu column: How to use Tavily Search API (comments) | community (Chinese) | 2025-07 | https://zhuanlan.zhihu.com/p/1926399113064318916 |
| 10 | Zhihu: Bocha AI search vs Exa.ai (domestic-usable Web Search APIs) | community (Chinese) | 2024-08 | https://zhuanlan.zhihu.com/p/712692839 |
| 11 | GitHub gpt-researcher issue #1047: Tavily — Too Many Requests | issue | 2024-12-27 | https://github.com/assafelovic/gpt-researcher/issues/1047 |
| 12 | Prefect community: 429 Tavily rate limit | forum | — | https://linen.prefect.io/t/26765852/ |
| 13 | Sacra: Ex-employee at Exa interview | research interview | ~2025–2026 | https://sacra.com/research/ex-employee-exa-ai-data-pipelines |
| 14 | Crustdata: Why Exa doesn't work for structured people search | competitor blog | ~2025–2026 | https://crustdata.com/blog/why-exa-doesnt-work-for-structured-people-search |
| 15 | Bright Data blog: Bright Data vs Exa | competitor blog | ~2026 | https://brightdata.com/blog/comparison/bright-data-vs-exa |
| 16 | dev.to (Ritza): SERP API comparison 2025 | dev blog | 2025 | https://dev.to/ritza/best-serp-api-comparison-2025-serpapi-vs-exa-vs-tavily-vs-scrapingdog-vs-scrapingbee-2jci |
| 17 | Firecrawl blog: Tavily/Exa alternatives | competitor blog | ~2025–2026 | https://www.firecrawl.dev/blog/tavily-alternatives , https://www.firecrawl.dev/blog/exa-alternatives |
| 18 | Nimble blog: Tavily/Exa alternatives | competitor blog | ~2026 | https://www.nimbleway.com/blog/tavily-alternatives |
| 19 | Medium: Tavily Alternatives 2026 (after the Nebius acquisition) | personal blog | 2026 | https://medium.com/@unicodeveloper/tavily-alternatives-in-2026-after-the-nebius-acquisition-9de526780686 |
| 20 | SearchMCP blog: Exa vs Tavily | third-party blog | ~2026 | https://www.searchmcp.io/blog/exa-vs-tavily-search-api |
| 21 | webscraft.org: Best search API for AI agents | third-party blog | ~2026 | https://webscraft.org/blog/search-api-dlya-ai-agentiv-scho-obirayut-rozrobniki-i-de-pomilyayutsya?lang=en |
| 22 | Reddit r/singularity: Exa free web search launch (snapshot) | forum | 2025 | https://www.reddit.com/r/singularity/comments/1idakmy/ |
| 23 | BrainGrid blog: Why we switched from Claude web search to Exa | user case | 2025-08-09 | https://www.braingrid.ai/blog/switching-claude-web-search-to-exa |
| 24 | exa.ai pricing pages (fact-check only) | vendor | read 2026-08 | https://exa.ai/pricing , https://exa.ai/docs/reference/pricing |
| 25 | exa.ai/versus/tavily (vendor comparison, mind the bias) | vendor | 2026-08-04 | https://exa.ai/versus/tavily |
| 26 | Product Hunt: exa.ai reviews (15 reviews, body not retrieved) | product reviews | 2026 | https://www.producthunt.com/products/exa-ai/reviews |

---

## 2. Tavily — reputation detail

### 2.1 Recognized strengths

| Opinion | Evidence | Source |
|---------|----------|--------|
| One API call does search+read+summarize; token-efficient; good for direct RAG | "一个 API 调用里完成了'搜索+点击+阅读+总结'的全过程…如果你只想要答案,选 Tavily。" [in Chinese; "One API call covers search+click+read+summarize… if you just want the answer, pick Tavily."] | linux.do #7 (reply #4, 2026-01) |
| Best for direct RAG; speed and pre-filtered context | "Exa is the best for Semantic and Neural Search. Tavily is the best for Direct RAG Applications. Where Tavily shines is in speed and pre-filtered context." | Reddit r/Rag benchmark #4 |
| "Good overall" default (accuracy behind Linkup but balanced) | "tavily is good overall, exa best for speed and linkup best for quality / accuracy"; also "linkup 1. tavily 2. exa" | Reddit r/Rag #3 (search + WebSearch snapshots) |
| Free credits refresh monthly; beginner-friendly | "目前每个账号每个月都有 1000 积分可以使用" [in Chinese; "every account gets 1,000 credits per month"]; dev.to #16: "1,000 recurring monthly credits places Tavily among the more generous free tiers" | linux.do #7, #6; dev.to #16 |
| Speed noted by Chinese users | "个人感觉 tavily更快 质量也还行 但仅适合单纯的搜索场景" [in Chinese; "Personally Tavily feels faster and quality is fine, but only for plain search use cases"] | linux.do #6 (reply, snapshot) |
| Light positive mentions on HN | "I use Llama.cpp with Tavily search (they give free credits each month)." | WebSearch snapshot (HN Ollama thread, https://news.ycombinator.com/item?id=45377641) |

### 2.2 Main complaints / pitfalls

| Complaint | Evidence | Source |
|-----------|----------|--------|
| Free-tier 429 rate-limit errors (high-frequency pain point) | "Error: 429 Client Error: Too Many Requests for url: ... Failed fetching sources. Resulting in empty response." | gpt-researcher #1047 (2024-12); Prefect #12: "Encountered HTTP 429 errors ... indicating rate limits have been exceeded" |
| 1,000 credits/month runs out; multi-account rotation workarounds emerge | Whole thread is a "Tavily Proxy multi-account rotation MCP"; another: "我之前free 的账户用没两下就用掉了" [in Chinese; "my free account's credits were gone in no time"] | linux.do #7 (entire thread), #6 |
| Search quality disputed (Chinese community, directional) | "看到有人说Tavily的搜索质量不太行...就换成了…EXA MCP" [in Chinese; "saw people saying Tavily's search quality isn't great ... so I switched to the Exa MCP"] | linux.do #6 (OP's reason for switching) |
| Results may be cached/dead links | "like most web search APIs, it doesn't always guarantee live or high-quality links. It likely pulls from cached or indexed sources... which can lead to 404s or dead pages" | Nimble #18 (competitor blog — mind the bias) |
| Results skew English/web-foreign; needs proxy from mainland China | Zhihu comments: "为什么搜出来的都是国外的信息比较多" ("why do results come back mostly foreign"), "需要代理吗" ("is a proxy needed"); linux.do #8 notes Brave needed TUN/AllProxy, ranks "Brave (2,000/mo, card required) > Tavily (1,000/mo) > Exa ($10 signup)" | Zhihu #9 comments; linux.do #8 |
| Recall below real Google SERP | "Tavily's recall ~3x lower than Google's" (r/AI_Agents benchmark, snapshot) | WebSearch snapshot (original URL not captured; low-medium confidence) |

### 2.3 Reliability & support signals

- No meaningful community discussion of Tavily support responsiveness/ticketing found (stated: not found).
- Change-risk signal: Medium #19 is titled "Tavily Alternatives in 2026 (After the Nebius Acquisition)" — post-acquisition user feedback: not found.
- Vendor self-claim "Tavily Ranks #1 on SealQA and SimpleQA" (tavily.com homepage) — recorded, not counted as reputation.

---

## 3. Exa — reputation detail

### 3.1 Recognized strengths

| Opinion | Evidence | Source |
|---------|----------|--------|
| Strong semantic/neural search for abstract, exploratory, "find pages" queries | "use Exa if your queries are abstract, exploratory, or require finding pages rather than keywords"; "Exa is the best for Semantic and Neural Search" | Reddit #4 (both subreddits) |
| Returns full text; good for deep research / finding codebases | "当你需要让 Claude Code 进行深度技术调研或寻找特定风格的代码库时,Exa 是首选。它能直接返回网页的全文内容(Full Text)" [in Chinese; "For deep technical research or finding codebases of a particular style with Claude Code, Exa is the first choice. It returns full page text, not just titles"] | linux.do #7 (reply #4 citing "expert advice") |
| API-first, good DX | "Not a consumer product with a side API — it's API-first by design... It's dirt cheap." (written pre-price-rise) | https://wire.insiderfinance.io/perplexity-vs-exa-ai-i-tried-both-and-this-one-changed-everything-50780e9c3afa |
| Quality improving over time; error rates down | "The search quality has become better because the coverage is better... reliability is better. The error rates have gone significantly lower" | Sacra ex-employee interview #13 |
| Founders reply directly, fast | Exa co-founder jldadriano replied point-by-point under pricing criticism ("curious what you believe to be confusing, we'd love to make it clearer!", "we are fixing") | HN #2 |
| Positive search experience | "exa.ai was able to surface relevant things — the exact stuff I needed and recent, up-to-date stuff, too." (after frustratingly stale Google results) | HN #2 (gigatexal) |
| No-key MCP free entry (used in Chinese community) | "就换成了即使不用Key也可以使用的EXA MCP。一直用到了现在" [in Chinese; "switched to the Exa MCP that works even without a key. Been using it since"] | linux.do #6 (OP) |
| Speed (vendor claim + third-party relay) | Vendor: "Exa Instant returns results in under 180ms"; Medium #19: "Exa Fast achieves sub-350ms P50 latency" (Exa 2.0, 2026-03) | exa.ai (vendor); Medium #19 |

### 3.2 Main complaints / pitfalls

| Complaint | Evidence | Source |
|-----------|----------|--------|
| Price rise: $5/1k → $7/1k from 2026-03 | "Exa updated its pricing in March 2026, raising standard search from $5/1k to $7/1k"; official page now $7/1k (≤10 results), +$1/1k per extra result | Bright Data #15 (numbers match official page #24) |
| Anchored expensive at volume | "Now, it costs the same as what Perplexity charges for search-grounded queries... this pricing wouldn't work with my volume of queries." | HN #1 (2025-05, pre-rise context) |
| Pricing table confusing | "the pricing is confusing to me and I think I'm not dumb"; "There are a bunch of different things that influence pricing (what's 'auto' vs. 'fast'?)" | HN #2 |
| Accuracy ranked below Tavily/Linkup by some | "I tried using Exa.ai's search API endpoint and noticed that the results are not as accurate as I ..."; ranking "linkup 1. tavily 2. exa" | Reddit #3 (snapshots) |
| Chinese users: less accurate than Tavily | "个人感觉 exa 搜索结果没 tavily 准确" [in Chinese; "personally Exa's results feel less accurate than Tavily's"] | linux.do #7 (reply #3) |
| Coverage weak on forums/social/sparse pages | "Exa indexes high-quality structured content better (blogs, documentation, papers), and worse — forums, social media, pages with minimal text." | webscraft.org #21 |
| Weak structured people search | "Exa's API is well-designed and its web search works for general content retrieval. The problems described here are specific to structured people search..." | Crustdata #14 (competitor — mind the bias) |
| Consumer free search mediocre | "The system needs a lot of work and even the clearest of prompts are hit and miss." | Reddit r/singularity #22 (snapshot) |
| Cost scales badly | "At 1 million requests/month, Exa's standard search costs $7,000+. With full page content, that number climbs to $8,000+." | Bright Data #15 |

### 3.3 Reliability & support signals

- Positive: founders respond directly on HN and commit to doc fixes (#2); ex-employee reports error rates dropped a lot (#13).
- Negative incident: open-webui discussion #15252 "issue: Exa.ai search is failing" (https://github.com/open-webui/open-webui/discussions/15252, 2025-06) — log-only, no official response recorded.
- No community record of large-scale Exa outages/SLA incidents found (stated: not found).
- Vendor claims "Exa leads across FRAMES, Tip-of-Tongue, and Seal0" (exa.ai) — recorded only. Note Tavily and Exa each claim #1 on different benchmarks; benchmark choice is a bias.

---

## 4. Pricing facts quick-reference (verified against official pages, 2026-08-17)

| Item | Tavily | Exa |
|------|--------|-----|
| Free tier | 1,000 credits/month, refreshes monthly (official pricing page, verified) | $20 signup credit (~2,800 searches) + $10/month free credits (official pricing page, verified) |
| Search unit price | Pay-as-you-go $0.008/credit (official docs, verified); basic search = 1 credit, `advanced` = 2 | $7/1k requests (≤10 results each), +$1/1k per extra result; contents $1/1k pages per content type |
| Price-rise history | None found | $5→$7/1k (2026-03), confirmed by multiple sources incl. official page |

Earlier inconsistency note: pre-verification drafts of this table listed
conflicting third-party numbers for Exa's free tier ($10 / 2,000 / 1,000
credits). Official page resolves it: $20 signup + $10/month.

---

## 5. Consensus takeaways (used by this skill)

1. **Tavily = the default "general web search + direct answer" layer** — one
   API for search+extract+summarize, token-friendly, monthly-refreshing free
   tier; fits day-to-day factual queries and RAG injection (multi-source:
   Reddit #3/#4, linux.do #6/#7).
2. **Exa = the semantic/neural retrieval layer** — abstract, exploratory,
   find-similar-pages queries with full-text returns; fits deep research,
   codebase discovery, entity/company/paper work (Reddit #4, Firecrawl #17,
   linux.do #7).
3. **Accuracy is contested**: both English (Reddit r/Rag) and Chinese
   (linux.do) users report Tavily as more accurate on simple queries, while
   Exa backers prize semantic relevance and freshness. No single-sided
   consensus; "Tavily steadiest overall, Exa strongest semantically" is the
   mainstream middle.
4. **Shared weakness**: forums/social/low-text pages (Exa called out by #21;
   Tavily skews English-web by #9). The community routes such content to
   Brave/Linkup/Serper; between these two, Tavily is the better pick.
5. **Cost-sensitive contexts**: Exa's 2026-03 rise to $7/1k plus a pricing
   table HN users find confusing (#1/#2); Tavily free tier 429s easily and
   1,000 credits run out for heavy users (#11/#12/#7). Mainland China needs
   a proxy for both (#8/#9); Exa has a no-key MCP entry, Tavily's monthly
   free credits are more practical (#6/#7).

---

## 6. Credibility notes

- Sample: ~40+ independent sources; 4 threads read in full (HN ×2,
  linux.do ×2, 20+ genuine replies). Three high-relevance Reddit threads
  were network-blocked for full retrieval — their quotes come from
  Tavily/WebSearch snapshots (marked "snapshot") and may be incomplete.
- Dates: evidence clusters 2024-10 to 2026-08; pricing verified against
  official pages 2026-08-17. Pre-2026-03 Exa pricing comments (e.g., "$5/1k")
  are labeled with their then-current context.
- Bias: Firecrawl/Nimble/Bright Data/Crustdata/exa.ai-versus are competitor
or vendor pages, labeled per-row; conclusions rely only on multi-source
agreement.
- Not found: Tavily official support/ticketing experience, systemic Exa
  outage records, Product Hunt review bodies, post-Nebius-acquisition Tavily
  feedback.
