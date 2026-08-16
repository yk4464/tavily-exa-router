# Tavily — Full Reference (as of 2026-08)

Docs: https://docs.tavily.com/documentation/api-reference/endpoint/search
Auth: `Authorization: Bearer $TAVILY_API_KEY` on all endpoints.
Base: `https://api.tavily.com`

## Endpoints

| Endpoint | Purpose | Notes |
|---|---|---|
| `POST /search` | Web search with snippets/scores | the workhorse |
| `POST /extract` | Fetch content for known URLs | the only real fetcher of the two services |
| `POST /map` | List URLs on a site | via CLI `tvly map` |
| `POST /crawl` | Crawl a site section | via CLI `tvly crawl` |

## /search parameters

| Parameter | Values / default | Notes |
|---|---|---|
| `query` | required | keep under ~400 chars; think keywords, not prompts |
| `search_depth` | `basic` (default) / `advanced` / `fast` / `ultra-fast` | advanced = 2 credits, modest quality gain; fast/ultra-fast **not recommended** (measured: duplicates, spam, no speed gain) |
| `max_results` | 0–20, default 5 | hard cap 20 (Exa allows 100) |
| `topic` | `general` / `news` / `finance` | vertical channels; `country` only works with `general` |
| `time_range` | `day` / `week` / `month` / `year` | convenience filter back from today |
| `start_date` / `end_date` | `YYYY-MM-DD` | precise window |
| `include_answer` | `false` / `basic` / `advanced` | LLM-synthesized answer in response |
| `include_raw_content` | bool / `markdown` / `text` | full page content; adds ~500ms (measured ~1.3s total) |
| `include_images` / `include_image_descriptions` / `include_favicon` | bool | image results, descriptions, icons |
| `include_domains` / `exclude_domains` | arrays (≤300 / ≤150) | domain allow/deny; strict (verified 5/5 arxiv-only) |
| `chunks_per_source` | 1–3 | content snippets per source |
| `auto_parameters` | bool | service auto-tunes params by intent |
| `exact_match` | bool | quoted-phrase only — **returned 0 results in testing; verify before relying on it** |
| `country` | ~190 names | boosts a country's results, `general` topic only; effect measured as weak |
| `include_usage` | bool | returns credit accounting |
| `safe_search` | bool | enterprise plans only |

## Response fields that matter

- `results[].score` — relevance score, always present. A heuristic filter,
  not a correctness signal: under ~0.3 is usually filler; keep low scores
  when recall matters and verify important claims against page content.
- `results[].content` — snippet (chunked when `chunks_per_source` > 1).
- `results[].published_date` — **almost never populated** (0/159 in testing).
  Do not rely on it; use Exa when dates matter.
- `answer` — present when `include_answer` set.
- `response_time`, `usage.credits` — latency and cost accounting.

## /extract

```json
POST /extract  {"urls": ["https://linux.do/t/topic/123", "..."]}
```
Returns `results[].raw_content` (markdown) and `failed_results[]` with errors.

Measured anti-block behavior (2026-08): succeeds on Discourse forums
(linux.do), X/Twitter profiles (real tweets incl. engagement context); blocked
or useless on zhihu.com (login wall), bilibili video pages (JS-only skeleton),
tieba.baidu.com (refused).

## Recipes

**Community opinions (Tavily's strength):**
```json
{"query": "<product> worth it complaints", "max_results": 8,
 "include_domains": ["reddit.com", "news.ycombinator.com"]}
```
Drop the `include_domains` filter for broader community coverage — Reddit/HN/
Quora surface naturally.

**Quick news scan:**
```json
{"query": "<topic>", "topic": "news", "time_range": "week", "max_results": 8}
```

**Answer without reading links:**
```json
{"query": "what is <concept>", "include_answer": "advanced", "max_results": 3}
```

**Academic-only when Exa is unavailable:**
```json
{"query": "<paper topic>", "include_domains": ["arxiv.org"], "max_results": 8}
```

## Pricing (2026-08)

- Basic search = 1 credit; `advanced` = 2 credits.
- Pay-as-you-go $0.008/credit; free tier 1,000 credits/month.
- `include_answer`, raw content, and images generally bill as part of the
  request credits — check current docs for edge cases.
