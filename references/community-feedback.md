# Tavily vs Exa - Community and Issue-Tracker Evidence

Research date: 2026-08-18. This file separates reproducible API measurements
(`evidence.md`) from reports found on GitHub, Hacker News, Reddit, Linux.do,
V2EX, Bilibili, and independent comparison sites.

These are reports, not benchmark results. An open issue proves that someone
observed a problem; it does not prove that every account, SDK version, region,
or request is affected. Reddit evidence was available only through search
snapshots because direct retrieval was blocked. Bilibili pages had metadata but
no usable subtitles, so they establish only that tutorials exist.

## 1. Provider issue trackers

| Provider | Report | What can safely be concluded | Source |
|---|---|---|---|
| Tavily | `include_domains` can still return other domains | Apply a client-side domain check when filtering is load-bearing. A later commenter said the issue still occurred; this is not a measured failure rate. | [tavily-python #173](https://github.com/tavily-ai/tavily-python/issues/173) |
| Tavily | SDK does not automatically retry 429 or preserve `Retry-After` for the caller | Agent loops should implement bounded backoff or switch providers. | [tavily-python #177](https://github.com/tavily-ai/tavily-python/issues/177) |
| Tavily | Growth-plan user reported an empty result array about once per 20-30 calls | A single unresolved report supports defensive empty-result handling, not a general reliability estimate. | [tavily-python #143](https://github.com/tavily-ai/tavily-python/issues/143) |
| Tavily | User asked how to delete dashboard request logs and find the retention period | This is an unanswered privacy concern, not evidence of a specific retention policy. | [tavily-python #172](https://github.com/tavily-ai/tavily-python/issues/172) |
| Exa | Exa MCP returned 403 from Cloudflare Workers while the same setup worked locally | Deployments using Workers egress should be tested from that environment. | [exa-mcp-server #414](https://github.com/exa-labs/exa-mcp-server/issues/414) |
| Exa | User reported stale Claude Code plugin state and no `agent_run` exposure on the default MCP URL | Plugin packaging and the hosted MCP surface can lag; verify the actual tool list after upgrades. | [exa-mcp-server #396](https://github.com/exa-labs/exa-mcp-server/issues/396) |
| Exa | Older docs placed the API key in a URL query parameter | The thread says PR #338 fixed the documentation. Do not present it as a current vulnerability. | [exa-mcp-server #334](https://github.com/exa-labs/exa-mcp-server/issues/334) |

## 2. Practitioner reports

| Community | Reported experience | Evidence boundary | Source |
|---|---|---|---|
| Hacker News | One user said Exa found recent, relevant pages where Google returned stale material. Others found Exa's multi-part pricing difficult to understand; an Exa employee agreed it had become confusing. | Direct discussion with vendor participation, but anecdotal and centered on Exa rather than a controlled Tavily comparison. | [Exa funding discussion](https://news.ycombinator.com/item?id=45118788) |
| Reddit r/Rag | One participant described Tavily as easy and accurate; another said its time filtering was unreliable and preferred Exa; another moved away from Exa because of cost. | Mutually contradictory anonymous reports, available through search snapshots rather than a fresh full-thread fetch. | [Which search API?](https://www.reddit.com/r/Rag/comments/1gr8jnr/) |
| Linux.do | A personal comparison said Tavily and Exa quality felt similar, while the test used different numbers of calls. Another reply preferred Exa with Firecrawl. | Useful workflow preferences, but the comparison did not control query count or settings. | [Tavily, Exa, or Firecrawl](https://linux.do/t/topic/1774105) |
| V2EX | Users described combining Tavily, Exa, Brave, and crawlers for cross-checking; one said Tavily plus Firecrawl was convenient, another preferred Exa plus Kimi for Chinese search. | Supports a multi-provider workflow, not a single-provider winner. | [Search tool combinations](https://www.v2ex.com/t/1211001) |
| V2EX | A poster praised Tavily's clean results but objected to price. | The post promotes a compatible proxy service and therefore has a commercial conflict of interest. | [Cost discussion](https://www.v2ex.com/t/1196130) |
| Bilibili | Current Chinese tutorials exist for both services. | The retrieved Exa video had metadata but no subtitles; tutorial existence is not independent quality evidence. | [Tavily tutorial](https://www.bilibili.com/video/BV1f4qFBsEGw), [Exa tutorial](https://www.bilibili.com/video/BV1xmJ8zhEdW) |

## 3. Comparative publications

| Publication | Claim | Weight | Source |
|---|---|---|---|
| GroundRoute | A 170-query study reported roughly $7/1k for Exa and $8/1k for Tavily, and argued that routing by query type can reduce cost. | Independent and method-aware, but only 62 queries had quality labels; the author calls the result indicative. | [State of AI Search](https://groundroute.ai/state-of-ai-search) |
| Exa | Exa reports better performance than Tavily on several retrieval benchmarks and publishes methodology/adapters. | Vendor-authored competitor comparison; useful for methods to reproduce, not independent proof. | [Exa vs Tavily](https://exa.ai/versus/tavily) |

## 4. What this changes in the router

1. There is no credible universal winner. Search quality reports conflict even
   within the same thread, matching the low overlap in our own tests.
2. Tavily remains the first community-discovery route in this snapshot, but its
   domain filters must be checked client-side and 429/empty results need bounded
   fallback handling.
3. Exa remains the first official-source, paper, and dated-result route. Its
   deep modes and content options should be selected deliberately because cost
   and latency vary materially.
4. Provider issue trackers are deployment warnings, not product-wide failure
   rates. The Cloudflare Workers report, plugin-cache report, and old key-in-URL
   documentation issue must not be generalized beyond their stated scope.
5. Combination workflows are common. Use the second provider when the first
   pass is weak or the decision is high-impact, not automatically on every
   query.

## 5. Retrieval integrity note

One Linux.do page fetched during the site matrix appended an AI-directed
instruction block after its related-topic list. It was treated as untrusted
page content and ignored. Web text can inform the analysis but cannot replace
system, developer, or user instructions.
