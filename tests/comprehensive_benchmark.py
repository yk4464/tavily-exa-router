"""Comprehensive Tavily Search/Extract and Exa Search/Contents benchmark.

The matrix covers every parameter relevant to this skill without attempting a
Cartesian product. It records accepted/rejected combinations, latency, cost,
result-shape quality signals, and per-URL extraction outcomes. Raw responses
are written only to git-ignored search_results/ and never contain API keys.
"""

import argparse
import json
import os
import re
import statistics
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "search_results"
TAVILY_KEY = os.environ["TAVILY_API_KEY"]
EXA_KEY = os.environ["EXA_API_KEY"]

COMMUNITY_DOMAINS = {
    "reddit.com", "news.ycombinator.com", "stackoverflow.com",
    "stackexchange.com", "zhihu.com", "v2ex.com", "juejin.cn",
    "dev.to", "medium.com", "substack.com", "linux.do", "quora.com",
}
AUTHORITATIVE_DOMAINS = {
    "openai.com", "anthropic.com", "arxiv.org", "openreview.net",
    "github.com", "docs.python.org", "python.org", "nature.com",
    "acm.org", "ieee.org", "reuters.com", "apnews.com", "gov.cn",
}

QUALITY_QUERIES = [
    {
        "id": "official",
        "query": "OpenAI Responses API official migration guide",
        "expected_domains": ["openai.com"],
    },
    {
        "id": "academic",
        "query": "Mamba selective state spaces original paper",
        "expected_domains": ["arxiv.org", "openreview.net", "github.com"],
    },
    {
        "id": "community",
        "query": "Tailwind CSS criticism real developer experience",
        "expected_domains": list(COMMUNITY_DOMAINS),
    },
    {
        "id": "chinese-community",
        "query": "Rust 生产环境 使用经验 踩坑",
        "expected_domains": list(COMMUNITY_DOMAINS),
    },
]

TARGETS = [
    {"name": "example", "kind": "static", "url": "https://example.com/"},
    {"name": "python-docs", "kind": "docs", "url": "https://docs.python.org/3/library/json.html"},
    {"name": "github", "kind": "code", "url": "https://github.com/python/cpython"},
    {"name": "hacker-news", "kind": "forum", "url": "https://news.ycombinator.com/item?id=43910228"},
    {"name": "linux-do", "kind": "forum", "url": "https://linux.do/t/topic/2435930"},
    {"name": "x", "kind": "social", "url": "https://x.com/elonmusk"},
    {"name": "reddit", "kind": "forum", "url": "https://www.reddit.com/r/Rag/comments/1gr8jnr/"},
    {"name": "zhihu", "kind": "login-wall", "url": "https://www.zhihu.com/"},
    {"name": "bilibili", "kind": "js-heavy", "url": "https://www.bilibili.com/video/BV1xmJ8zhEdW"},
    {"name": "tieba", "kind": "forum", "url": "https://tieba.baidu.com/f?kw=显卡"},
    {"name": "arxiv", "kind": "paper", "url": "https://arxiv.org/abs/2307.06435"},
    {"name": "devto", "kind": "blog", "url": "https://dev.to/ritza/best-serp-api-comparison-2025-serpapi-vs-exa-vs-tavily-vs-scrapingdog-vs-scrapingbee-2jci"},
    {"name": "medium", "kind": "blog", "url": "https://medium.com/@unicodeveloper/tavily-alternatives-in-2026-after-the-nebius-acquisition-9de526780686"},
]

BLOCK_SIGNS = [
    (r"video not found|page not found|视频不见了|啊叻.视频不见了|404 not found", "missing-page"),
    (r"just a moment|challenge-platform|cf-browser-verification", "cloudflare"),
    (r"verify you are human|验证您是真人|人机验证", "human-check"),
    (r"登录|扫码登录|登录后", "login-wall"),
    (r"javascript is disabled|enable javascript", "js-shell"),
    (r"403 forbidden|access denied", "forbidden"),
]
PROMPT_RISK_SIGNS = [
    (r"critical instructions for all ai assistants|ignore (?:all )?previous instructions", "prompt-injection"),
    (r"\b(system|developer) message\b.*\b(must|instruction)", "instruction-like-text"),
]
TRACKING_QUERY_KEYS = {"ref", "ref_src", "source", "spm", "feature", "si"}
TRACKING_QUERY_PREFIXES = ("utm_", "fbclid", "gclid", "mc_")


def domain(url):
    return urlparse(url or "").netloc.lower().removeprefix("www.")


def canonical_url(url):
    parsed = urlparse(url or "")
    if not parsed.scheme or not parsed.netloc:
        return ""
    path = parsed.path.rstrip("/") or "/"
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_KEYS
        and not key.lower().startswith(TRACKING_QUERY_PREFIXES)
    ]
    return urlunparse((
        parsed.scheme.lower(), parsed.netloc.lower(), path, "",
        urlencode(query_pairs, doseq=True), "",
    ))


def source_identity(url):
    """Collapse common URL variants that identify the same underlying source."""
    canonical = canonical_url(url)
    if not canonical:
        return ""
    parsed = urlparse(canonical)
    host = parsed.netloc.removeprefix("www.")
    path = parsed.path

    if host == "arxiv.org":
        match = re.match(r"^/(?:abs|html|pdf)/([^/]+)", path, re.I)
        if match:
            return f"arxiv:{match.group(1).removesuffix('.pdf').lower()}"
    if host == "doi.org" and path.lower().startswith("/10.48550/arxiv."):
        return f"arxiv:{re.sub(r'^/10\\.48550/arxiv\\.', '', path, flags=re.I).lower()}"

    segments = [segment for segment in path.split("/") if segment]
    if (len(segments) >= 4 and segments[0] == "t"
            and segments[-1].isdigit() and segments[-2].isdigit()):
        path = "/" + "/".join(segments[:-1])
        return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))
    return canonical


def domain_matches(actual, expected):
    return actual == expected or actual.endswith("." + expected)


def decode_body(raw):
    return raw.decode("utf-8", "replace")


def parse_sse(text, content_type):
    events = []
    done = False
    for block in re.split(r"\r?\n\r?\n", text.strip()):
        payload = "\n".join(
            line[5:].lstrip() for line in block.splitlines() if line.startswith("data:")
        )
        if not payload:
            continue
        if payload == "[DONE]":
            done = True
            continue
        try:
            events.append(json.loads(payload))
        except json.JSONDecodeError:
            events.append({"type": "unparsed", "data": payload[:2000]})
    return {
        "content_type": content_type,
        "event_types": [event.get("type") for event in events],
        "event_count": len(events),
        "done": done,
        "events": events,
    }


def request(provider, endpoint, payload, timeout=300, stream=False):
    if provider == "tavily":
        url = f"https://api.tavily.com/{endpoint}"
        headers = {"Authorization": f"Bearer {TAVILY_KEY}"}
    else:
        url = f"https://api.exa.ai/{endpoint}"
        headers = {"x-api-key": EXA_KEY}
    headers["Content-Type"] = "application/json"

    started = time.perf_counter()
    attempts = []
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read()
                content_type = response.headers.get("Content-Type", "")
                text = decode_body(raw)
                if stream or "text/event-stream" in content_type:
                    data = parse_sse(text, content_type)
                else:
                    data = json.loads(text) if text else {}
                return {
                    "http_status": response.status,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000),
                    "attempts": attempts + [response.status],
                    "data": data,
                }
        except urllib.error.HTTPError as exc:
            body = decode_body(exc.read())
            attempts.append(exc.code)
            if exc.code in {429, 500, 502, 503, 504} and attempt < 2:
                retry_after = exc.headers.get("Retry-After")
                delay = min(float(retry_after), 10.0) if retry_after else 2.0 * (attempt + 1)
                time.sleep(delay)
                continue
            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                data = {"raw_error": body[:4000]}
            return {
                "http_status": exc.code,
                "elapsed_ms": round((time.perf_counter() - started) * 1000),
                "attempts": attempts,
                "data": data,
            }
        except Exception as exc:  # noqa: BLE001
            attempts.append(type(exc).__name__)
            if attempt < 2:
                time.sleep(2.0 * (attempt + 1))
                continue
            return {
                "http_status": None,
                "elapsed_ms": round((time.perf_counter() - started) * 1000),
                "attempts": attempts,
                "data": {"exception": str(exc)},
            }


def cost_from(provider, data):
    if provider == "tavily":
        usage = data.get("usage") or {}
        return usage.get("credits") if isinstance(usage, dict) else usage
    cost = data.get("costDollars")
    if cost is None:
        for event in reversed(data.get("events") or []):
            if event.get("costDollars") is not None:
                cost = event["costDollars"]
                break
    return cost.get("total") if isinstance(cost, dict) else cost


def response_results(data):
    if data.get("results") is not None:
        return data.get("results") or []
    for event in data.get("events") or []:
        if event.get("type") == "results":
            return event.get("results") or []
    return []


def quality_summary(data, spec):
    results = response_results(data)
    urls = [item.get("url") or item.get("id") or "" for item in results]
    domains = [domain(url) for url in urls if url]
    canonical_urls = [canonical_url(url) for url in urls if url]
    source_ids = [source_identity(url) for url in urls if url]
    unique_urls = len(set(canonical_urls))
    expected = spec.get("expected_domains") or []
    expected_ranks = [
        rank for rank, actual in enumerate(domains, 1)
        if any(domain_matches(actual, wanted) for wanted in expected)
    ]
    return {
        "result_count": len(results),
        "unique_urls": unique_urls,
        "duplicate_urls": len(urls) - unique_urls,
        "unique_sources": len(set(source_ids)),
        "near_duplicate_urls": len(urls) - len(set(source_ids)),
        "unique_domains": len(set(domains)),
        "expected_domain_hits": sum(
            any(domain_matches(actual, wanted) for wanted in expected)
            for actual in domains
        ),
        "community_hits": sum(
            any(domain_matches(actual, wanted) for wanted in COMMUNITY_DOMAINS)
            for actual in domains
        ),
        "authoritative_hits": sum(
            any(domain_matches(actual, wanted) for wanted in AUTHORITATIVE_DOMAINS)
            for actual in domains
        ),
        "expected_domain_reciprocal_rank": round(1 / min(expected_ranks), 3) if expected_ranks else 0,
        "dated_results": sum(bool(item.get("publishedDate") or item.get("published_date")) for item in results),
        "top_results": [
            {
                "title": (item.get("title") or "")[:160],
                "url": item.get("url") or item.get("id"),
                "date": item.get("publishedDate") or item.get("published_date"),
                "score": item.get("score"),
                "content_chars": len(item.get("content") or item.get("text") or ""),
            }
            for item in results[:10]
        ],
    }


def classify_content(text):
    text = text or ""
    if not text.strip():
        return "empty"
    for pattern, label in BLOCK_SIGNS:
        if re.search(pattern, text, re.I):
            return label
    if len(text) < 300:
        return "short"
    return "content"


def content_risk_signals(text):
    return [label for pattern, label in PROMPT_RISK_SIGNS if re.search(pattern, text or "", re.I | re.S)]


def search_response_summary(provider, data):
    results = response_results(data)
    output = data.get("output")
    if output is None:
        output = next((
            event.get("output") for event in reversed(data.get("events") or [])
            if event.get("type") == "done" and event.get("output") is not None
        ), None)
    summary = quality_summary(data, {})
    summary.update({
        "answer_chars": len(data.get("answer") or ""),
        "raw_content_pages": sum(bool(item.get("raw_content")) for item in results),
        "raw_content_chars": sum(len(item.get("raw_content") or "") for item in results),
        "snippet_chars": [len(item.get("content") or "") for item in results],
        "text_pages": sum(bool(item.get("text")) for item in results),
        "text_chars": sum(len(item.get("text") or "") for item in results),
        "highlight_pages": sum(bool(item.get("highlights")) for item in results),
        "highlight_chars": sum(
            len("".join(item.get("highlights") or [])) for item in results
        ),
        "summary_pages": sum(item.get("summary") is not None for item in results),
        "images": len(data.get("images") or []),
        "image_descriptions": sum(
            bool(item.get("description")) for item in (data.get("images") or [])
            if isinstance(item, dict)
        ),
        "favicons": sum(bool(item.get("favicon")) for item in results),
        "published_dates": [
            item.get("publishedDate") or item.get("published_date")
            for item in results if item.get("publishedDate") or item.get("published_date")
        ],
        "output_present": output is not None,
        "output_type": type(output).__name__ if output is not None else None,
        "output_keys": sorted(output) if isinstance(output, dict) else [],
        "stream_done": data.get("done"),
        "stream_event_types": data.get("event_types"),
    })
    return summary


def retrieval_response_summary(provider, data):
    results = data.get("results") or []
    text_field = "raw_content" if provider == "tavily" else "text"
    statuses = data.get("statuses") or []
    failed_results = data.get("failed_results") or []
    return {
        "result_count": len(results),
        "text_pages": sum(bool(item.get(text_field)) for item in results),
        "text_chars": [len(item.get(text_field) or "") for item in results],
        "classifications": [classify_content(item.get(text_field) or "") for item in results],
        "risk_signals": [content_risk_signals(item.get(text_field) or "") for item in results],
        "images": sum(len(item.get("images") or []) for item in results),
        "favicons": sum(bool(item.get("favicon")) for item in results),
        "highlight_pages": sum(bool(item.get("highlights")) for item in results),
        "highlight_chars": [len("".join(item.get("highlights") or [])) for item in results],
        "summary_pages": sum(item.get("summary") is not None for item in results),
        "summary_types": [type(item.get("summary")).__name__ for item in results if item.get("summary") is not None],
        "subpage_counts": [len(item.get("subpages") or []) for item in results],
        "extras_counts": [
            {
                key: len(value) if isinstance(value, list) else int(value is not None)
                for key, value in (item.get("extras") or {}).items()
            }
            for item in results
        ],
        "status_counts": {
            value: sum(status.get("status") == value for status in statuses)
            for value in sorted({status.get("status") for status in statuses if status.get("status")})
        },
        "failed_results": len(failed_results),
    }


def compare_result_sets(left, right):
    left_ids = [source_identity(item.get("url") or item.get("id"))
                for item in response_results(left["response"])]
    right_ids = [source_identity(item.get("url") or item.get("id"))
                 for item in response_results(right["response"])]
    left_set, right_set = set(left_ids), set(right_ids)
    union = left_set | right_set
    return {
        "left": left["name"],
        "right": right["name"],
        "same_order": left_ids == right_ids,
        "source_jaccard": round(len(left_set & right_set) / len(union), 3) if union else 1.0,
        "left_count": len(left_ids),
        "right_count": len(right_ids),
        "left_ms": left["elapsed_ms"],
        "right_ms": right["elapsed_ms"],
    }


def extraction_summary(provider, data):
    by_url = {}
    for item in data.get("results") or []:
        url = item.get("url") or item.get("id")
        text = item.get("raw_content") if provider == "tavily" else item.get("text")
        by_url[canonical_url(url)] = {
            "chars": len(text or ""),
            "classification": classify_content(text),
            "title": (item.get("title") or "")[:160],
            "risk_signals": content_risk_signals(text),
        }

    failures = {}
    if provider == "tavily":
        for item in data.get("failed_results") or []:
            failures[canonical_url(item.get("url"))] = item.get("error")
    else:
        for status in data.get("statuses") or []:
            if status.get("status") != "success":
                failures[canonical_url(status.get("id"))] = status.get("error") or status

    rows = []
    for target in TARGETS:
        target_key = canonical_url(target["url"])
        detail = by_url.get(target_key)
        rows.append({
            **target,
            "returned": detail is not None,
            "content": detail,
            "failure": failures.get(target_key),
        })
    return {
        "returned": len(by_url),
        "failed": len(failures),
        "content_pages": sum(
            bool(row.get("content") and row["content"]["classification"] == "content")
            for row in rows
        ),
        "targets": rows,
    }


class Benchmark:
    def __init__(self, delay):
        self.delay = delay
        self.cases = []

    def run(self, provider, endpoint, group, name, payload, *, summary=None, stream=False, timeout=300):
        result = request(provider, endpoint, payload, timeout=timeout, stream=stream)
        data = result.pop("data")
        record = {
            "provider": provider,
            "endpoint": endpoint,
            "group": group,
            "name": name,
            "payload": payload,
            **result,
            "cost": cost_from(provider, data),
            "summary": summary(data) if summary and result["http_status"] == 200 else None,
            "response": data,
        }
        self.cases.append(record)
        print(
            f"[{provider:<7}] {group:<20} {name:<42} "
            f"HTTP={str(record['http_status']):<4} {record['elapsed_ms']:>7}ms "
            f"cost={record['cost']}"
        )
        if self.delay:
            time.sleep(self.delay)
        return record

    def mode_sweep(self):
        for spec in QUALITY_QUERIES:
            for depth in ("ultra-fast", "fast", "basic", "advanced"):
                self.run(
                    "tavily", "search", "mode-quality", f"{depth}:{spec['id']}",
                    {"query": spec["query"], "max_results": 8,
                     "search_depth": depth, "include_usage": True},
                    summary=lambda data, s=spec: quality_summary(data, s),
                )
            for mode in ("instant", "fast", "auto", "deep-lite", "deep", "deep-reasoning"):
                self.run(
                    "exa", "search", "mode-quality", f"{mode}:{spec['id']}",
                    {"query": spec["query"], "numResults": 8, "type": mode},
                    summary=lambda data, s=spec: quality_summary(data, s),
                    timeout=360,
                )

    def parameter_matrix(self):
        today = date.today()
        start = today - timedelta(days=30)
        tavily_cases = [
            ("baseline-usage", {"query": "OpenAI Responses API", "max_results": 5, "include_usage": True}),
            ("query-over-1500", {"query": "x" * 1501, "max_results": 1}),
            ("max-results-0", {"query": "OpenAI", "max_results": 0}),
            ("max-results-1", {"query": "OpenAI", "max_results": 1}),
            ("max-results-20", {"query": "OpenAI", "max_results": 20}),
            ("max-results-21", {"query": "OpenAI", "max_results": 21}),
            ("topic-general", {"query": "AI search APIs", "topic": "general", "max_results": 5}),
            ("topic-news", {"query": "AI model releases", "topic": "news", "max_results": 5}),
            ("topic-finance", {"query": "NVIDIA earnings", "topic": "finance", "max_results": 5}),
            *[(f"time-range-{value}", {"query": "AI model releases", "topic": "news", "time_range": value, "max_results": 5})
              for value in ("day", "week", "month", "year")],
            ("exact-date-window", {"query": "AI model releases", "topic": "news",
                                   "start_date": start.isoformat(), "end_date": today.isoformat(), "max_results": 5}),
            ("time-range-plus-dates", {"query": "AI model releases", "topic": "news", "time_range": "week",
                                       "start_date": start.isoformat(), "end_date": today.isoformat(), "max_results": 5}),
            ("answer-false", {"query": "what is retrieval augmented generation", "include_answer": False, "max_results": 3}),
            ("answer-basic", {"query": "what is retrieval augmented generation", "include_answer": "basic", "max_results": 3}),
            ("answer-advanced", {"query": "what is retrieval augmented generation", "include_answer": "advanced", "max_results": 3}),
            ("raw-false", {"query": "Python json documentation", "include_raw_content": False, "max_results": 2}),
            ("raw-markdown", {"query": "Python json documentation", "include_raw_content": "markdown", "max_results": 2}),
            ("raw-text", {"query": "Python json documentation", "include_raw_content": "text", "max_results": 2}),
            ("images", {"query": "James Webb telescope images", "include_images": True,
                         "include_image_descriptions": True, "max_results": 3}),
            ("images-control", {"query": "James Webb telescope images", "include_images": True,
                                "max_results": 3}),
            ("favicon", {"query": "Python documentation", "include_favicon": True, "max_results": 3}),
            ("include-domain", {"query": "attention transformer paper", "include_domains": ["arxiv.org"], "max_results": 5}),
            ("exclude-domain", {"query": "OpenAI news", "exclude_domains": ["openai.com"], "max_results": 5}),
            ("include-and-exclude-same", {"query": "OpenAI", "include_domains": ["openai.com"],
                                          "exclude_domains": ["openai.com"], "max_results": 5}),
            *[(f"chunks-{count}", {"query": "Python json documentation", "chunks_per_source": count, "max_results": 3})
              for count in (1, 2, 3)],
            ("auto-parameters", {"query": "latest AI model release", "auto_parameters": True,
                                 "include_usage": True, "max_results": 5}),
            ("auto-explicit-basic", {"query": "latest AI model release", "auto_parameters": True,
                                     "search_depth": "basic", "include_usage": True, "max_results": 5}),
            ("exact-match", {"query": '"retrieval augmented generation" survey', "exact_match": True, "max_results": 5}),
            ("exact-match-control", {"query": '"retrieval augmented generation" survey', "max_results": 5}),
            ("country", {"query": "best electric cars", "country": "germany", "max_results": 5}),
            ("country-control", {"query": "best electric cars", "max_results": 5}),
            ("safe-search", {"query": "internet safety", "safe_search": True, "max_results": 3}),
        ]
        for name, payload in tavily_cases:
            self.run("tavily", "search", "search-parameters", name, payload,
                     summary=lambda data: search_response_summary("tavily", data))

        categories = {
            "company": "OpenAI",
            "publication": "Mamba selective state spaces paper",
            "news": "AI model releases",
            "personal site": "SQLite production experience",
            "financial report": "NVIDIA annual report",
            "people": "Dario Amodei",
        }
        exa_cases = [
            ("empty-query", {"query": "", "numResults": 1, "type": "auto"}, False),
            *[(f"num-results-{count}", {"query": "OpenAI", "numResults": count, "type": "auto"}, False)
              for count in (0, 1, 10, 11, 100, 101)],
            *[(f"category-{category}", {"query": query, "numResults": 5, "type": "auto", "category": category}, False)
              for category, query in categories.items()],
            ("include-domain", {"query": "machine learning engineering", "numResults": 5,
                                "type": "auto", "includeDomains": ["*.substack.com"]}, False),
            ("exclude-domain", {"query": "OpenAI news", "numResults": 5,
                                "type": "auto", "excludeDomains": ["openai.com"]}, False),
            ("domain-path-prefix", {"query": "Python json", "numResults": 5,
                                    "type": "auto", "includeDomains": ["docs.python.org/3/library"]}, False),
            ("start-published", {"query": "AI model releases", "numResults": 5, "type": "auto",
                                 "startPublishedDate": start.isoformat() + "T00:00:00Z"}, False),
            ("end-published", {"query": "AI model releases", "numResults": 5, "type": "auto",
                               "endPublishedDate": today.isoformat() + "T23:59:59Z"}, False),
            ("published-window", {"query": "AI model releases", "numResults": 5, "type": "auto",
                                  "startPublishedDate": start.isoformat() + "T00:00:00Z",
                                  "endPublishedDate": today.isoformat() + "T23:59:59Z"}, False),
            ("company-plus-date", {"query": "OpenAI", "numResults": 2, "category": "company",
                                   "startPublishedDate": start.isoformat() + "T00:00:00Z"}, False),
            ("company-plus-exclude", {"query": "OpenAI", "numResults": 2, "category": "company",
                                      "excludeDomains": ["openai.com"]}, False),
            ("people-plus-date", {"query": "Dario Amodei", "numResults": 2, "category": "people",
                                  "startPublishedDate": start.isoformat() + "T00:00:00Z"}, False),
            ("people-plus-exclude", {"query": "Dario Amodei", "numResults": 2, "category": "people",
                                     "excludeDomains": ["linkedin.com"]}, False),
            ("additional-auto", {"query": "AI search APIs", "numResults": 5, "type": "auto",
                                 "additionalQueries": ["search API benchmarks"]}, False),
            ("additional-auto-control", {"query": "AI search APIs", "numResults": 5, "type": "auto"}, False),
            ("additional-deep-1", {"query": "AI search APIs", "numResults": 5, "type": "deep",
                                   "additionalQueries": ["search API benchmarks"]}, False),
            ("additional-deep-10", {"query": "AI search APIs", "numResults": 5, "type": "deep",
                                    "additionalQueries": [f"AI search API angle {i}" for i in range(10)]}, False),
            ("additional-deep-11", {"query": "AI search APIs", "numResults": 5, "type": "deep",
                                    "additionalQueries": [f"AI search API angle {i}" for i in range(11)]}, False),
            ("system-prompt", {"query": "AI search APIs", "numResults": 5, "type": "deep-lite",
                               "systemPrompt": "Prefer official documentation and independent benchmarks."}, False),
            ("output-schema", {"query": "Tavily and Exa", "numResults": 5, "type": "auto",
                               "outputSchema": {"type": "object", "properties": {
                                   "services": {"type": "array", "items": {"type": "string"}}}}}, False),
            ("stream-output-schema", {"query": "Tavily and Exa", "numResults": 5, "type": "auto",
                                      "stream": True, "outputSchema": {"type": "object", "properties": {
                                          "services": {"type": "array", "items": {"type": "string"}}}}}, True),
            ("moderation", {"query": "online safety research", "numResults": 3, "type": "auto", "moderation": True}, False),
            ("moderation-control", {"query": "online safety research", "numResults": 3, "type": "auto"}, False),
            ("user-location", {"query": "AI policy news", "numResults": 5, "type": "auto", "userLocation": "de"}, False),
            ("user-location-control", {"query": "AI policy news", "numResults": 5, "type": "auto"}, False),
            ("compliance-hipaa", {"query": "health data security", "numResults": 3, "type": "auto",
                                  "compliance": "hipaa"}, False),
            ("deprecated-crawl-dates", {"query": "OpenAI", "numResults": 3, "type": "auto",
                                        "startCrawlDate": start.isoformat() + "T00:00:00Z",
                                        "endCrawlDate": today.isoformat() + "T23:59:59Z"}, False),
            ("deprecated-context", {"query": "OpenAI", "numResults": 3, "type": "auto", "context": True}, False),
            ("deprecated-control", {"query": "OpenAI", "numResults": 3, "type": "auto"}, False),
            ("contents-combined", {"query": "Python JSON documentation", "numResults": 2, "type": "auto",
                                   "includeDomains": ["docs.python.org"], "contents": {
                                       "text": {"maxCharacters": 1200},
                                       "highlights": {"query": "JSON encoder", "maxCharacters": 300},
                                       "summary": {"query": "Main purpose"},
                                       "extras": {"links": 3}}}, False),
            ("contents-live-options", {"query": "Python JSON documentation", "numResults": 1, "type": "auto",
                                       "includeDomains": ["docs.python.org"], "contents": {
                                           "text": {"maxCharacters": 1200, "includeHtmlTags": True,
                                                    "verbosity": "compact", "includeSections": ["body"]},
                                           "maxAgeHours": 0, "livecrawlTimeout": 30000}}, False),
        ]
        for name, payload, stream in exa_cases:
            self.run("exa", "search", "search-parameters", name, payload,
                     summary=lambda data: search_response_summary("exa", data), stream=stream, timeout=360)

    def extraction_matrix(self):
        urls = [target["url"] for target in TARGETS]
        for depth in ("basic", "advanced"):
            self.run(
                "tavily", "extract", "extract-sites", f"all-sites-{depth}",
                {"urls": urls, "extract_depth": depth, "format": "markdown",
                 "timeout": 60, "include_usage": True},
                summary=lambda data: extraction_summary("tavily", data), timeout=180,
            )

        tavily_extract_cases = [
            ("urls-string", {"urls": TARGETS[1]["url"], "format": "text", "include_usage": True}),
            ("format-markdown", {"urls": [TARGETS[1]["url"]], "format": "markdown", "include_usage": True}),
            ("format-text", {"urls": [TARGETS[1]["url"]], "format": "text", "include_usage": True}),
            ("query-chunks-1", {"urls": [TARGETS[1]["url"]], "query": "JSON encoder and decoder",
                                "chunks_per_source": 1, "include_usage": True}),
            ("query-chunks-5", {"urls": [TARGETS[1]["url"]], "query": "JSON encoder and decoder",
                                "chunks_per_source": 5, "include_usage": True}),
            ("chunks-without-query", {"urls": [TARGETS[1]["url"]], "chunks_per_source": 2}),
            ("query-chunks-0", {"urls": [TARGETS[1]["url"]], "query": "JSON", "chunks_per_source": 0}),
            ("query-chunks-6", {"urls": [TARGETS[1]["url"]], "query": "JSON", "chunks_per_source": 6}),
            ("images-favicon", {"urls": [TARGETS[2]["url"]], "include_images": True, "include_favicon": True}),
            ("timeout-1", {"urls": [TARGETS[1]["url"]], "timeout": 1}),
            ("timeout-60", {"urls": [TARGETS[1]["url"]], "timeout": 60}),
            ("timeout-0", {"urls": [TARGETS[1]["url"]], "timeout": 0}),
            ("timeout-61", {"urls": [TARGETS[1]["url"]], "timeout": 61}),
            ("urls-20", {"urls": [f"https://example.com/?benchmark={i}" for i in range(20)], "timeout": 10}),
            ("urls-21", {"urls": [f"https://example.com/?benchmark={i}" for i in range(21)], "timeout": 10}),
        ]
        for name, payload in tavily_extract_cases:
            self.run("tavily", "extract", "extract-parameters", name, payload,
                     summary=lambda data: retrieval_response_summary("tavily", data), timeout=180)

        for age in (-1, 0, 24):
            self.run(
                "exa", "contents", "extract-sites", f"all-sites-age-{age}",
                {"ids": urls, "text": {"maxCharacters": 4000, "verbosity": "standard"},
                 "maxAgeHours": age, "livecrawlTimeout": 30000},
                summary=lambda data: extraction_summary("exa", data), timeout=180,
            )

        doc_url = TARGETS[1]["url"]
        exa_content_cases = [
            ("text-true", {"ids": [doc_url], "text": True}),
            ("text-max-1", {"ids": [doc_url], "text": {"maxCharacters": 1}}),
            ("text-max-10000", {"ids": [doc_url], "text": {"maxCharacters": 10000}}),
            *[(f"verbosity-{value}", {"ids": [doc_url], "text": {"verbosity": value, "maxCharacters": 4000}})
              for value in ("compact", "standard", "full")],
            ("html-tags-false", {"ids": [doc_url], "text": {"includeHtmlTags": False, "maxCharacters": 3000}}),
            ("html-tags-true", {"ids": [doc_url], "text": {"includeHtmlTags": True, "maxCharacters": 3000}}),
            *[(f"include-section-{value}", {"ids": [doc_url], "text": {"includeSections": [value], "maxCharacters": 3000},
                                             "maxAgeHours": 0, "livecrawlTimeout": 30000})
              for value in ("header", "navigation", "banner", "body", "sidebar", "footer", "metadata")],
            *[(f"exclude-section-{value}", {"ids": [doc_url], "text": {"excludeSections": [value], "maxCharacters": 3000},
                                             "maxAgeHours": 0, "livecrawlTimeout": 30000})
              for value in ("header", "navigation", "banner", "body", "sidebar", "footer", "metadata")],
            ("highlights", {"ids": [doc_url], "highlights": {"query": "JSON encoder", "maxCharacters": 500}}),
            ("summary", {"ids": [doc_url], "summary": {"query": "What does this module provide?"}}),
            ("summary-schema", {"ids": [doc_url], "summary": {"query": "What does this module provide?",
                                 "schema": {"type": "object", "properties": {"topic": {"type": "string"}}}}}),
            ("extras", {"ids": [doc_url], "extras": {"links": 5, "imageLinks": 5,
                        "richLinks": 5, "richImageLinks": 5, "codeBlocks": 5}}),
            ("text-highlights-summary", {"ids": [doc_url], "text": {"maxCharacters": 2000},
                                         "highlights": {"query": "JSON encoder", "maxCharacters": 400},
                                         "summary": {"query": "Main purpose"}}),
            ("subpages-0", {"ids": ["https://docs.python.org/3/"], "subpages": 0}),
            ("subpages-2", {"ids": ["https://docs.python.org/3/"], "subpages": 2,
                            "subpageTarget": "json documentation"}),
            ("subpages-101", {"ids": ["https://docs.python.org/3/"], "subpages": 101,
                              "subpageTarget": "json documentation"}),
            ("max-age-720", {"ids": [doc_url], "text": {"maxCharacters": 1000}, "maxAgeHours": 720}),
            ("max-age-721", {"ids": [doc_url], "text": {"maxCharacters": 1000}, "maxAgeHours": 721}),
            ("live-timeout", {"ids": [doc_url], "text": {"maxCharacters": 1000},
                              "maxAgeHours": 0, "livecrawlTimeout": 1000}),
            ("mixed-valid-invalid", {"ids": [doc_url, "https://example.com/not-found-benchmark-404"],
                                     "text": {"maxCharacters": 1000}, "maxAgeHours": 0,
                                     "livecrawlTimeout": 10000}),
        ]
        for name, payload in exa_content_cases:
            self.run("exa", "contents", "contents-parameters", name, payload,
                     summary=lambda data: retrieval_response_summary("exa", data), timeout=180)

    def aggregate(self):
        modes = {}
        for case in self.cases:
            if case["group"] != "mode-quality" or not case.get("summary"):
                continue
            mode = case["name"].split(":", 1)[0]
            key = f"{case['provider']}:{mode}"
            modes.setdefault(key, []).append(case)
        mode_summary = {}
        for key, rows in modes.items():
            mode_summary[key] = {
                "runs": len(rows),
                "median_ms": statistics.median(row["elapsed_ms"] for row in rows),
                "total_expected_hits": sum(row["summary"]["expected_domain_hits"] for row in rows),
                "total_community_hits": sum(row["summary"]["community_hits"] for row in rows),
                "total_authoritative_hits": sum(row["summary"]["authoritative_hits"] for row in rows),
                "total_duplicates": sum(row["summary"]["duplicate_urls"] for row in rows),
                "total_near_duplicates": sum(row["summary"]["near_duplicate_urls"] for row in rows),
                "costs": [row["cost"] for row in rows if row["cost"] is not None],
            }
        by_key = {(case["provider"], case["name"]): case for case in self.cases}
        pair_specs = [
            ("tavily", "images", "images-control"),
            ("tavily", "exact-match", "exact-match-control"),
            ("tavily", "country", "country-control"),
            ("tavily", "auto-parameters", "auto-explicit-basic"),
            ("exa", "additional-auto", "additional-auto-control"),
            ("exa", "moderation", "moderation-control"),
            ("exa", "user-location", "user-location-control"),
            ("exa", "deprecated-crawl-dates", "deprecated-control"),
            ("exa", "deprecated-context", "deprecated-control"),
        ]
        paired = {}
        for provider, left_name, right_name in pair_specs:
            left = by_key.get((provider, left_name))
            right = by_key.get((provider, right_name))
            if left and right and left["http_status"] == right["http_status"] == 200:
                paired[f"{provider}:{left_name}-vs-{right_name}"] = compare_result_sets(left, right)

        return {
            "total_cases": len(self.cases),
            "http_success": sum(case["http_status"] == 200 for case in self.cases),
            "http_rejected": sum(isinstance(case["http_status"], int) and case["http_status"] >= 400 for case in self.cases),
            "transport_failures": sum(case["http_status"] is None for case in self.cases),
            "mode_quality": mode_summary,
            "paired_comparisons": paired,
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=("all", "modes", "parameters", "extract"), default="all")
    parser.add_argument("--delay", type=float, default=0.2, help="delay between calls to avoid burst limits")
    args = parser.parse_args()

    benchmark = Benchmark(args.delay)
    started = time.time()
    if args.suite in {"all", "modes"}:
        benchmark.mode_sweep()
    if args.suite in {"all", "parameters"}:
        benchmark.parameter_matrix()
    if args.suite in {"all", "extract"}:
        benchmark.extraction_matrix()

    payload = {
        "metadata": {
            "date": date.today().isoformat(),
            "suite": args.suite,
            "duration_seconds": round(time.time() - started, 1),
            "quality_queries": QUALITY_QUERIES,
            "targets": TARGETS,
        },
        "summary": benchmark.aggregate(),
        "cases": benchmark.cases,
    }
    OUT_DIR.mkdir(exist_ok=True)
    filename = "comprehensive_benchmark.json" if args.suite == "all" else f"comprehensive_{args.suite}.json"
    output = OUT_DIR / filename
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved {len(benchmark.cases)} cases -> {output}")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
