"""Full parameter sweep and SKILL.md fact probes for Tavily and Exa.

Covers every official /search parameter on both providers, key /extract and
/contents parameters, documented limits/400 rejections, deprecated fields, and
SKILL.md factual claims (pricing, defaults, date behavior, site reachability).

Stdlib-only. Reads TAVILY_API_KEY and EXA_API_KEY from the environment and
never writes credentials to disk or stdout.
"""

import argparse
import datetime
import email.utils
import http.client
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_OUT_DIR = Path(__file__).resolve().parent.parent / "search_results"
TAVILY_SEARCH_URL = "https://api.tavily.com/search"
TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"
TAVILY_USAGE_URL = "https://api.tavily.com/usage"
EXA_SEARCH_URL = "https://api.exa.ai/search"
EXA_CONTENTS_URL = "https://api.exa.ai/contents"

RETRY_STATUSES = {408, 429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3

SITE_TARGETS = [
    ("docs", "https://docs.python.org/3/library/json.html"),
    ("github", "https://github.com/python/cpython"),
    ("hn", "https://news.ycombinator.com/item?id=43910228"),
    ("bilibili", "https://www.bilibili.com/video/BV1xmJ8zhEdW"),
    ("tieba", "https://tieba.baidu.com/f?kw=%E6%98%BE%E5%8D%A1"),
    ("x", "https://x.com/elonmusk"),
    ("reddit", "https://www.reddit.com/r/Rag/comments/1gr8jnr/"),
    ("zhihu", "https://www.zhihu.com/"),
]


def api_key(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"missing environment variable {name}; set it before running this script"
        )
    return value


def _retry_after(exc, fallback):
    headers = getattr(exc, "headers", None)
    header = headers.get("Retry-After") if headers is not None else None
    if not header:
        return fallback
    try:
        seconds = float(header)
    except ValueError:
        try:
            when = email.utils.parsedate_to_datetime(header)
        except (TypeError, ValueError):
            return fallback
        if when is None:
            return fallback
        if when.tzinfo is None:
            when = when.replace(tzinfo=datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        seconds = (when - now).total_seconds()
    if seconds != seconds or seconds < 0:
        return fallback
    return min(seconds, 15.0)


def request_json(url, payload, headers, method="POST", timeout=120):
    """Send HTTP request with bounded retry on transient 429/5xx/transport errors."""
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req_headers = dict(headers)
    if data is not None:
        req_headers.setdefault("Content-Type", "application/json")

    for attempt in range(MAX_ATTEMPTS):
        last = attempt + 1 == MAX_ATTEMPTS
        t0 = time.perf_counter()
        req = urllib.request.Request(
            url, data=data, headers=req_headers, method=method
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
                ctype = resp.headers.get("Content-Type", "")
                text = raw.decode("utf-8", errors="replace")
                if "text/event-stream" in ctype.lower():
                    return {
                        "http_status": resp.status,
                        "elapsed_ms": elapsed_ms,
                        "content_type": ctype,
                        "stream_text": text,
                        "data": None,
                        "error_body": None,
                    }
                return {
                    "http_status": resp.status,
                    "elapsed_ms": elapsed_ms,
                    "content_type": ctype,
                    "data": json.loads(text) if text.strip() else {},
                    "error_body": None,
                }
        except urllib.error.HTTPError as exc:
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code in RETRY_STATUSES and not last:
                time.sleep(_retry_after(exc, 2.0 * (attempt + 1)))
                continue
            parsed_err = None
            try:
                parsed_err = json.loads(body)
            except ValueError:
                parsed_err = None
            return {
                "http_status": exc.code,
                "elapsed_ms": elapsed_ms,
                "content_type": exc.headers.get("Content-Type", "")
                if exc.headers
                else "",
                "data": parsed_err,
                "error_body": body[:2000],
            }
        except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as exc:
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            if not last:
                time.sleep(2.0 * (attempt + 1))
                continue
            return {
                "http_status": None,
                "elapsed_ms": elapsed_ms,
                "content_type": "",
                "data": None,
                "error_body": f"{type(exc).__name__}: {exc}",
            }
    raise AssertionError("unreachable")


def summarize_tavily_search(resp):
    data = resp.get("data")
    if resp.get("http_status") != 200 or not isinstance(data, dict):
        return {"error": resp.get("error_body")}
    results = data.get("results") or []
    urls = [r.get("url", "") for r in results]
    domains = [urlparse(u).netloc.lower().removeprefix("www.") for u in urls]
    has_pub_key = ["published_date" in r for r in results]
    non_null_pub = [r.get("published_date") for r in results if r.get("published_date")]
    content_lens = [len(r.get("content") or "") for r in results]
    raw_lens = [len(r.get("raw_content") or "") for r in results if r.get("raw_content")]
    scores = [r.get("score") for r in results if "score" in r]
    return {
        "count": len(results),
        "credits": (data.get("usage") or {}).get("credits"),
        "response_time_s": data.get("response_time"),
        "answer_len": len(data.get("answer") or ""),
        "images_count": len(data.get("images") or []),
        "image_has_desc": any(
            isinstance(im, dict) and bool(im.get("description"))
            for im in (data.get("images") or [])
        ),
        "has_favicon": any(bool(r.get("favicon")) for r in results),
        "has_published_date_key": sum(has_pub_key),
        "non_null_published_dates": len(non_null_pub),
        "sample_dates": non_null_pub[:3],
        "has_raw_content": len(raw_lens),
        "avg_content_len": round(sum(content_lens) / len(content_lens), 1)
        if content_lens
        else 0,
        "has_ellipsis_sep": any("[...]" in (r.get("content") or "") for r in results),
        "scores_present": len(scores),
        "auto_parameters": data.get("auto_parameters"),
        "domains": domains,
        "urls": urls,
    }


def summarize_tavily_extract(resp):
    data = resp.get("data")
    if resp.get("http_status") != 200 or not isinstance(data, dict):
        return {"error": resp.get("error_body")}
    results = data.get("results") or []
    failed = data.get("failed_results") or []
    return {
        "credits": (data.get("usage") or {}).get("credits"),
        "ok_count": len(results),
        "failed_count": len(failed),
        "ok_urls": [
            {
                "url": r.get("url"),
                "raw_len": len(r.get("raw_content") or ""),
                "snippet": (r.get("raw_content") or "")[:180],
                "images": len(r.get("images") or []),
                "favicon": bool(r.get("favicon")),
                "published_date": r.get("published_date"),
            }
            for r in results
        ],
        "failed_urls": failed,
    }


def summarize_exa_search(resp):
    if resp.get("stream_text") is not None:
        text = resp["stream_text"]
        has_done = "[DONE]" in text
        types = re.findall(r'"type"\s*:\s*"([^"]+)"', text)
        return {
            "stream": True,
            "bytes": len(text),
            "has_done_marker": has_done,
            "event_types": sorted(set(types)),
        }
    data = resp.get("data")
    if resp.get("http_status") != 200 or not isinstance(data, dict):
        return {"error": resp.get("error_body")}
    results = data.get("results") or []
    urls = [r.get("url", "") for r in results]
    domains = [urlparse(u).netloc.lower().removeprefix("www.") for u in urls]
    dates = [r.get("publishedDate") for r in results if r.get("publishedDate")]
    return {
        "count": len(results),
        "cost_total": (data.get("costDollars") or {}).get("total"),
        "costDollars": data.get("costDollars"),
        "searchTime_ms": data.get("searchTime"),
        "resolvedSearchType": data.get("resolvedSearchType"),
        "warnings": data.get("warnings"),
        "notices": data.get("notices"),
        "dated_count": len(dates),
        "sample_dates": [d[:10] for d in dates[:4]],
        "scores_present": sum(1 for r in results if r.get("score") is not None),
        "has_text": sum(1 for r in results if r.get("text")),
        "has_highlights": sum(1 for r in results if r.get("highlights")),
        "has_summary": sum(1 for r in results if r.get("summary")),
        "has_subpages": sum(1 for r in results if r.get("subpages")),
        "has_extras": sum(1 for r in results if r.get("extras")),
        "has_context": "context" in data,
        "has_output": "output" in data,
        "output_keys": list((data.get("output") or {}).keys())
        if isinstance(data.get("output"), dict)
        else None,
        "grounding_count": len((data.get("output") or {}).get("grounding") or [])
        if isinstance(data.get("output"), dict)
        else 0,
        "domains": domains,
        "urls": urls,
    }


def summarize_exa_contents(resp):
    data = resp.get("data")
    if resp.get("http_status") != 200 or not isinstance(data, dict):
        return {"error": resp.get("error_body")}
    results = data.get("results") or []
    statuses = data.get("statuses") or []
    return {
        "costDollars": data.get("costDollars"),
        "result_count": len(results),
        "results_summary": [
            {
                "url": r.get("url"),
                "text_len": len(r.get("text") or ""),
                "highlights_count": len(r.get("highlights") or []),
                "has_summary": bool(r.get("summary")),
                "subpages_count": len(r.get("subpages") or []),
                "extras_keys": list((r.get("extras") or {}).keys()),
                "snippet": (r.get("text") or "")[:180],
            }
            for r in results
        ],
        "statuses": statuses,
    }


def build_cases():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    today = now_utc.date()
    d7 = (today - datetime.timedelta(days=7)).isoformat()
    d30 = (today - datetime.timedelta(days=30)).isoformat()
    today_s = today.isoformat()
    now_iso = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    d7_iso = f"{d7}T00:00:00Z"
    d30_iso = f"{d30}T00:00:00Z"
    today_end_iso = f"{today_s}T23:59:59Z"

    cases = []

    def add(suite, name, provider, endpoint, payload, est_tavily=0, est_exa=0.0,
            extra_headers=None, timeout=120):
        cases.append({
            "suite": suite,
            "name": name,
            "provider": provider,
            "endpoint": endpoint,
            "payload": payload,
            "est_tavily": est_tavily,
            "est_exa": est_exa,
            "extra_headers": extra_headers or {},
            "timeout": timeout,
        })

    # --- 1. Tavily /search full parameter sweep ---
    ts = "tavily-search"
    add(ts, "tv:ctrl_basic", "tavily", "search",
        {"query": "Python requests library", "max_results": 5, "search_depth": "basic", "include_usage": True}, 1)
    add(ts, "tv:ctrl_omitted_max", "tavily", "search",
        {"query": "Python requests library", "include_usage": True}, 1)
    add(ts, "tv:query_empty", "tavily", "search", {"query": "", "max_results": 1}, 0)
    add(ts, "tv:query_1501", "tavily", "search",
        {"query": ("python " * 215)[:1501], "max_results": 1, "include_usage": True}, 1)
    add(ts, "tv:max_results_0", "tavily", "search", {"query": "Python", "max_results": 0}, 0)
    add(ts, "tv:max_results_20", "tavily", "search",
        {"query": "Python requests", "max_results": 20, "include_usage": True}, 1)
    add(ts, "tv:max_results_21", "tavily", "search", {"query": "Python requests", "max_results": 21}, 0)

    add(ts, "tv:depth_advanced", "tavily", "search",
        {"query": "Python requests library", "max_results": 5, "search_depth": "advanced", "include_usage": True}, 2)
    add(ts, "tv:depth_fast", "tavily", "search",
        {"query": "Python requests library", "max_results": 5, "search_depth": "fast", "include_usage": True}, 1)
    add(ts, "tv:depth_ultrafast", "tavily", "search",
        {"query": "Python requests library", "max_results": 5, "search_depth": "ultra-fast", "include_usage": True}, 1)
    add(ts, "tv:chunks_1", "tavily", "search",
        {"query": "Python requests library", "max_results": 3, "search_depth": "basic", "chunks_per_source": 1}, 1)
    add(ts, "tv:chunks_4_oob", "tavily", "search",
        {"query": "Python requests library", "max_results": 3, "chunks_per_source": 4}, 0)

    add(ts, "tv:topic_news", "tavily", "search",
        {"query": "AI model releases", "topic": "news", "max_results": 5, "include_usage": True}, 1)
    add(ts, "tv:topic_finance", "tavily", "search",
        {"query": "NVIDIA quarterly earnings", "topic": "finance", "max_results": 5, "include_usage": True}, 1)
    add(ts, "tv:country_general", "tavily", "search",
        {"query": "best electric cars", "topic": "general", "country": "germany", "max_results": 5}, 1)
    add(ts, "tv:country_ctrl", "tavily", "search",
        {"query": "best electric cars", "topic": "general", "max_results": 5}, 1)
    add(ts, "tv:country_news_conflict", "tavily", "search",
        {"query": "electric cars", "topic": "news", "country": "germany", "max_results": 3}, 0)

    add(ts, "tv:time_range_d_alias", "tavily", "search",
        {"query": "AI model releases", "topic": "news", "time_range": "d", "max_results": 5}, 1)
    add(ts, "tv:time_range_week", "tavily", "search",
        {"query": "AI model releases", "topic": "news", "time_range": "week", "max_results": 5}, 1)
    add(ts, "tv:start_end_date", "tavily", "search",
        {"query": "AI model releases", "topic": "general", "start_date": d30, "end_date": today_s, "max_results": 5}, 1)
    add(ts, "tv:time_range_plus_dates", "tavily", "search",
        {"query": "AI model releases", "time_range": "week", "start_date": d30, "max_results": 3}, 0)
    add(ts, "tv:include_pub_date", "tavily", "search",
        {"query": "AI model releases", "topic": "general", "include_published_date": True, "max_results": 5, "include_usage": True}, 1)
    add(ts, "tv:filter_by_pub_date", "tavily", "search",
        {"query": "AI model releases", "topic": "general", "start_date": d30, "filter_by_published_date": True, "max_results": 5, "include_usage": True}, 1)
    add(ts, "tv:max_age_neg1", "tavily", "search",
        {"query": "Python requests library", "max_age_hours": -1, "max_results": 3, "include_usage": True}, 1)
    add(ts, "tv:max_age_0", "tavily", "search",
        {"query": "Python requests library", "max_age_hours": 0, "max_results": 3, "include_usage": True}, 1)
    add(ts, "tv:max_age_24", "tavily", "search",
        {"query": "Python requests library", "max_age_hours": 24, "max_results": 3, "include_usage": True}, 1)
    add(ts, "tv:max_age_721_oob", "tavily", "search",
        {"query": "Python requests library", "max_age_hours": 721, "max_results": 3}, 0)

    add(ts, "tv:answer_basic", "tavily", "search",
        {"query": "what is retrieval augmented generation", "include_answer": "basic", "max_results": 3, "include_usage": True}, 1)
    add(ts, "tv:answer_advanced", "tavily", "search",
        {"query": "what is retrieval augmented generation", "include_answer": "advanced", "max_results": 3, "include_usage": True}, 1)
    add(ts, "tv:raw_markdown", "tavily", "search",
        {"query": "Python json documentation", "include_raw_content": "markdown", "max_results": 2, "include_usage": True}, 1)
    add(ts, "tv:raw_text", "tavily", "search",
        {"query": "Python json documentation", "include_raw_content": "text", "max_results": 2, "include_usage": True}, 1)
    add(ts, "tv:images_desc_favicon", "tavily", "search",
        {"query": "James Webb space telescope", "include_images": True, "include_image_descriptions": True, "include_favicon": True, "max_results": 3, "include_usage": True}, 1)

    add(ts, "tv:domains_restrict", "tavily", "search",
        {"query": "transformer attention", "include_domains": ["arxiv.org"], "include_domains_mode": "restrict", "max_results": 5}, 1)
    add(ts, "tv:domains_prefer", "tavily", "search",
        {"query": "best specialty coffee roasters Tokyo", "include_domains": ["arxiv.org"], "include_domains_mode": "prefer", "max_results": 5}, 1)
    add(ts, "tv:domains_mode_no_inc", "tavily", "search",
        {"query": "Python", "include_domains_mode": "prefer", "max_results": 3}, 0)
    add(ts, "tv:exclude_domains", "tavily", "search",
        {"query": "Python requests documentation", "exclude_domains": ["pypi.org"], "max_results": 5}, 1)

    add(ts, "tv:lang_boost", "tavily", "search",
        {"query": "Rust async runtime", "language": "zh-cn", "max_results": 5}, 1)
    add(ts, "tv:lang_filter", "tavily", "search",
        {"query": "Rust async runtime", "language": "zh-cn", "filter_by_language": True, "max_results": 5}, 1)
    add(ts, "tv:lang_filter_no_lang", "tavily", "search",
        {"query": "Rust async runtime", "filter_by_language": True, "max_results": 3}, 0)

    add(ts, "tv:auto_params_only", "tavily", "search",
        {"query": "latest AI model release detailed comparison", "auto_parameters": True, "include_usage": True, "max_results": 5}, 2)
    add(ts, "tv:auto_params_explicit_basic", "tavily", "search",
        {"query": "latest AI model release detailed comparison", "auto_parameters": True, "search_depth": "basic", "include_usage": True, "max_results": 5}, 2)
    add(ts, "tv:exact_match", "tavily", "search",
        {"query": '"retrieval augmented generation" survey', "exact_match": True, "max_results": 5}, 1)
    add(ts, "tv:exact_match_ctrl", "tavily", "search",
        {"query": '"retrieval augmented generation" survey', "max_results": 5}, 1)
    add(ts, "tv:safe_search_basic", "tavily", "search",
        {"query": "internet safety", "search_depth": "basic", "safe_search": True, "max_results": 3}, 1)
    add(ts, "tv:safe_search_fast", "tavily", "search",
        {"query": "internet safety", "search_depth": "fast", "safe_search": True, "max_results": 3}, 0)
    add(ts, "tv:safe_search_ultrafast", "tavily", "search",
        {"query": "internet safety", "search_depth": "ultra-fast", "safe_search": True, "max_results": 3}, 0)

    # --- 2. Tavily /extract key parameters & sites ---
    te = "tavily-extract"
    add(te, "tv_ext:sites_matrix", "tavily", "extract",
        {"urls": [u for _, u in SITE_TARGETS], "extract_depth": "basic", "format": "markdown", "timeout": 60, "include_usage": True}, 2, timeout=180)
    add(te, "tv_ext:url_string", "tavily", "extract",
        {"urls": "https://example.com/", "include_usage": True}, 1)
    add(te, "tv_ext:depth_advanced", "tavily", "extract",
        {"urls": ["https://docs.python.org/3/library/json.html"], "extract_depth": "advanced", "include_usage": True}, 2)
    add(te, "tv_ext:format_text", "tavily", "extract",
        {"urls": ["https://docs.python.org/3/library/json.html"], "format": "text"}, 1)
    add(te, "tv_ext:query_chunks_1", "tavily", "extract",
        {"urls": ["https://docs.python.org/3/library/json.html"], "query": "JSON encoder and decoder", "chunks_per_source": 1}, 1)
    add(te, "tv_ext:query_chunks_5", "tavily", "extract",
        {"urls": ["https://docs.python.org/3/library/json.html"], "query": "JSON encoder and decoder", "chunks_per_source": 5}, 1)
    add(te, "tv_ext:chunks_oob_0", "tavily", "extract",
        {"urls": ["https://example.com/"], "query": "example", "chunks_per_source": 0}, 0)
    add(te, "tv_ext:chunks_oob_6", "tavily", "extract",
        {"urls": ["https://example.com/"], "query": "example", "chunks_per_source": 6}, 0)
    add(te, "tv_ext:images_favicon_pubdate", "tavily", "extract",
        {"urls": ["https://github.com/python/cpython"], "include_images": True, "include_favicon": True, "include_published_date": True}, 1)
    add(te, "tv_ext:timeout_0", "tavily", "extract",
        {"urls": ["https://example.com/"], "timeout": 0}, 0)
    add(te, "tv_ext:timeout_61", "tavily", "extract",
        {"urls": ["https://example.com/"], "timeout": 61}, 1)
    add(te, "tv_ext:urls_21", "tavily", "extract",
        {"urls": [f"https://example.com/?p={i}" for i in range(21)]}, 0)
    add(te, "tv_ext:mixed_valid_invalid", "tavily", "extract",
        {"urls": ["https://example.com/", "https://example.com/nonexistent-404-probe"]}, 1)

    # --- 3. Exa /search full parameter sweep ---
    es = "exa-search"
    add(es, "exa:type_omitted", "exa", "search", {"query": "Python requests library", "numResults": 3}, 0, 0.007)
    add(es, "exa:type_lite", "exa", "search", {"query": "Python requests library", "numResults": 8, "type": "lite"}, 0, 0.004)
    add(es, "exa:type_instant", "exa", "search", {"query": "Python requests library", "numResults": 8, "type": "instant"}, 0, 0.004)
    add(es, "exa:type_auto", "exa", "search", {"query": "Python requests library", "numResults": 8, "type": "auto"}, 0, 0.007)
    add(es, "exa:type_fast", "exa", "search", {"query": "Python requests library", "numResults": 8, "type": "fast"}, 0, 0.007)
    add(es, "exa:type_deep", "exa", "search", {"query": "Python requests library", "numResults": 3, "type": "deep"}, 0, 0.012, timeout=240)
    add(es, "exa:type_deep_lite", "exa", "search", {"query": "Python requests library", "numResults": 3, "type": "deep-lite"}, 0, 0.012, timeout=240)
    add(es, "exa:type_deep_reasoning", "exa", "search", {"query": "Python requests library", "numResults": 3, "type": "deep-reasoning"}, 0, 0.015, timeout=240)
    add(es, "exa:type_neural_dep", "exa", "search", {"query": "Python requests library", "numResults": 3, "type": "neural"}, 0, 0.007)
    add(es, "exa:type_keyword_dep", "exa", "search", {"query": "Python requests library", "numResults": 3, "type": "keyword"}, 0, 0.007)

    add(es, "exa:query_empty", "exa", "search", {"query": "", "numResults": 1, "type": "lite"}, 0, 0.0)
    add(es, "exa:num_0", "exa", "search", {"query": "OpenAI", "numResults": 0, "type": "lite"}, 0, 0.0)
    add(es, "exa:num_11", "exa", "search", {"query": "OpenAI", "numResults": 11, "type": "lite"}, 0, 0.005)
    add(es, "exa:num_100", "exa", "search", {"query": "OpenAI", "numResults": 100, "type": "lite"}, 0, 0.094)
    add(es, "exa:num_101", "exa", "search", {"query": "OpenAI", "numResults": 101, "type": "lite"}, 0, 0.0)

    cat_queries = [
        ("news", "AI model releases"),
        ("company", "OpenAI"),
        ("publication", "Mamba selective state spaces"),
        ("personal site", "SQLite production experience"),
        ("financial report", "NVIDIA annual report"),
        ("people", "Dario Amodei"),
    ]
    for cat, q in cat_queries:
        add(es, f"exa:lite_cat_{cat.replace(' ', '_')}", "exa", "search",
            {"query": q, "numResults": 3, "type": "lite", "category": cat}, 0, 0.004)

    add(es, "exa:company_plus_date", "exa", "search",
        {"query": "OpenAI", "numResults": 2, "type": "lite", "category": "company", "startPublishedDate": d30_iso}, 0, 0.0)
    add(es, "exa:people_plus_date", "exa", "search",
        {"query": "Dario Amodei", "numResults": 2, "type": "lite", "category": "people", "startPublishedDate": d30_iso}, 0, 0.0)
    add(es, "exa:people_plus_exclude", "exa", "search",
        {"query": "Dario Amodei", "numResults": 2, "type": "lite", "category": "people", "excludeDomains": ["linkedin.com"]}, 0, 0.0)
    add(es, "exa:company_plus_exclude", "exa", "search",
        {"query": "OpenAI", "numResults": 2, "type": "lite", "category": "company", "excludeDomains": ["openai.com"]}, 0, 0.004)

    add(es, "exa:lite_accepted_combo", "exa", "search",
        {
            "query": "AI model releases",
            "numResults": 5,
            "type": "lite",
            "startPublishedDate": d7_iso,
            "endPublishedDate": today_end_iso,
            "includeDomains": ["openai.com", "anthropic.com"],
            "excludeDomains": ["medium.com"],
            "userLocation": "US",
            "moderation": True,
            "objective": "Find official model release announcements",
            "userIdentifier": "drift_probe_1",
            "metadata": {"suite": "param_sweep"},
        }, 0, 0.004)
    add(es, "exa:start_pub_now", "exa", "search",
        {"query": "AI model releases", "numResults": 8, "type": "lite", "startPublishedDate": now_iso}, 0, 0.004)
    add(es, "exa:user_loc_coords", "exa", "search",
        {"query": "coffee shops near me", "numResults": 3, "type": "lite",
         "userLocation": {"country": "US", "latitude": 37.7749, "longitude": -122.4194}}, 0, 0.004)
    add(es, "exa:user_id_invalid", "exa", "search",
        {"query": "OpenAI", "numResults": 1, "type": "lite", "userIdentifier": "bad@email.com"}, 0, 0.0)
    add(es, "exa:wildcard_domains", "exa", "search",
        {"query": "machine learning engineering", "numResults": 3, "type": "lite", "includeDomains": ["*.substack.com"]}, 0, 0.004)
    add(es, "exa:compliance_hipaa", "exa", "search",
        {"query": "health data security", "numResults": 1, "type": "lite", "compliance": "hipaa"}, 0, 0.0)

    add(es, "exa:lite_contents_text_hl", "exa", "search",
        {"query": "Python json documentation", "numResults": 3, "type": "lite",
         "contents": {"text": {"maxCharacters": 500}, "highlights": {"query": "JSON encoder", "maxCharacters": 200}}}, 0, 0.004)
    add(es, "exa:lite_snapshot", "exa", "search",
        {"query": "Python release notes", "numResults": 2, "type": "lite",
         "contents": {"snapshotAsOf": "2026-10-01"}}, 0, 0.004)

    # Documented `lite` rejections (400 naming field)
    lite_rejects = [
        ("outputSchema", {"outputSchema": {"type": "text", "description": "Summary"}}),
        ("contents.summary", {"contents": {"summary": {"query": "Main point"}}}),
        ("contents.maxAgeHours", {"contents": {"maxAgeHours": -1}}),
        ("systemPrompt", {"systemPrompt": "Prefer official docs."}),
        ("stream", {"stream": True}),
        ("additionalQueries", {"additionalQueries": ["Python http"]}),
        ("contents.extras", {"contents": {"extras": {"links": 2}}}),
        ("contents.subpages", {"contents": {"subpages": 1}}),
        ("contents.livecrawl", {"contents": {"livecrawl": "never"}}),
        ("contents.livecrawlTimeout", {"contents": {"livecrawlTimeout": 5000}}),
        ("startCrawlDate", {"startCrawlDate": d30_iso}),
        ("includeText", {"includeText": ["Python"]}),
        ("contents.context", {"contents": {"context": True}}),
    ]
    for label, extra in lite_rejects:
        p = {"query": "Python requests", "numResults": 1, "type": "lite", **extra}
        add(es, f"exa:lite_reject_{label}", "exa", "search", p, 0, 0.0)

    # outputSchema, stream, systemPrompt, additionalQueries on auto/deep
    add(es, "exa:auto_schema_obj", "exa", "search",
        {"query": "best vector databases 2026", "numResults": 5, "type": "auto",
         "outputSchema": {"type": "object", "properties": {
             "databases": {"type": "array", "items": {"type": "object", "properties": {
                 "name": {"type": "string"}, "url": {"type": "string"}}}}}}}, 0, 0.007)
    add(es, "exa:auto_schema_text", "exa", "search",
        {"query": "what is Tavily search", "numResults": 3, "type": "auto",
         "outputSchema": {"type": "text", "description": "One concise sentence"}}, 0, 0.007)
    add(es, "exa:schema_11_props", "exa", "search",
        {"query": "OpenAI", "numResults": 2, "type": "auto",
         "outputSchema": {"type": "object", "properties": {f"f{i}": {"type": "string"} for i in range(11)}}}, 0, 0.0)
    add(es, "exa:schema_3_levels", "exa", "search",
        {"query": "OpenAI", "numResults": 2, "type": "auto",
         "outputSchema": {"type": "object", "properties": {
             "a": {"type": "object", "properties": {
                 "b": {"type": "object", "properties": {"c": {"type": "string"}}}}}}}}, 0, 0.0)
    add(es, "exa:schema_array_no_items", "exa", "search",
        {"query": "OpenAI", "numResults": 2, "type": "auto",
         "outputSchema": {"type": "object", "properties": {"arr": {"type": "array"}}}}, 0, 0.0)
    add(es, "exa:auto_stream_schema", "exa", "search",
        {"query": "Tavily vs Exa", "numResults": 3, "type": "auto", "stream": True,
         "outputSchema": {"type": "text", "description": "Two bullet points"}}, 0, 0.007)
    add(es, "exa:auto_stream_no_schema", "exa", "search",
        {"query": "Tavily vs Exa", "numResults": 3, "type": "auto", "stream": True}, 0, 0.007)
    add(es, "exa:auto_system_prompt", "exa", "search",
        {"query": "AI search APIs", "numResults": 3, "type": "auto",
         "systemPrompt": "Prefer official documentation over blog posts."}, 0, 0.007)
    add(es, "exa:additional_on_auto", "exa", "search",
        {"query": "Python requests library", "numResults": 5, "type": "auto",
         "additionalQueries": ["urllib3 connection pool python"]}, 0, 0.007)
    add(es, "exa:additional_on_deep_1", "exa", "search",
        {"query": "Python requests library", "numResults": 3, "type": "deep",
         "additionalQueries": ["urllib3 connection pool python"]}, 0, 0.012, timeout=240)
    add(es, "exa:additional_on_deep_11", "exa", "search",
        {"query": "Python requests library", "numResults": 3, "type": "deep",
         "additionalQueries": [f"query variant {i}" for i in range(11)]}, 0, 0.0)

    # auto contents + deprecated fields
    add(es, "exa:auto_contents_summary", "exa", "search",
        {"query": "Python json documentation", "numResults": 2, "type": "auto",
         "contents": {"summary": {"query": "Main purpose"}}}, 0, 0.009)
    add(es, "exa:auto_contents_extras", "exa", "search",
        {"query": "Python json documentation", "numResults": 2, "type": "auto",
         "contents": {"extras": {"links": 3, "imageLinks": 2, "richImageLinks": 2, "richLinks": 2, "codeBlocks": 2}}}, 0, 0.007)
    add(es, "exa:auto_max_age_0", "exa", "search",
        {"query": "Python json documentation", "numResults": 1, "type": "auto",
         "includeDomains": ["docs.python.org"],
         "contents": {"text": {"maxCharacters": 500}, "maxAgeHours": 0, "livecrawlTimeout": 10000}}, 0, 0.007)
    add(es, "exa:auto_dyn_hl_no_hdr", "exa", "search",
        {"query": "Python json documentation", "numResults": 2, "type": "auto",
         "contents": {"highlights": {"dynamic": True}}}, 0, 0.0)
    add(es, "exa:auto_dyn_hl_with_hdr", "exa", "search",
        {"query": "Python json documentation", "numResults": 2, "type": "auto",
         "contents": {"highlights": {"dynamic": True}}}, 0, 0.007,
        extra_headers={"Exa-Beta": "dynamic-highlights-2026-08-28"})
    add(es, "exa:auto_dep_crawl_dates", "exa", "search",
        {"query": "Python requests library", "numResults": 3, "type": "auto",
         "startCrawlDate": d30_iso, "endCrawlDate": today_end_iso}, 0, 0.007)
    add(es, "exa:auto_dep_context", "exa", "search",
        {"query": "Python requests library", "numResults": 3, "type": "auto", "context": True}, 0, 0.007)
    add(es, "exa:auto_dep_livecrawl", "exa", "search",
        {"query": "Python requests library", "numResults": 2, "type": "auto",
         "contents": {"livecrawl": "never", "text": {"maxCharacters": 300}}}, 0, 0.007)
    add(es, "exa:auto_dep_subpages", "exa", "search",
        {"query": "Tavily API", "numResults": 2, "type": "auto",
         "contents": {"subpages": 1, "subpageTarget": "pricing"}}, 0, 0.007)
    add(es, "exa:auto_dep_include_text", "exa", "search",
        {"query": "Python requests library", "numResults": 2, "type": "auto",
         "includeText": ["Session"]}, 0, 0.007)
    add(es, "exa:bearer_auth", "exa", "search",
        {"query": "Python requests", "numResults": 1, "type": "lite"}, 0, 0.004,
        extra_headers={"__USE_BEARER__": "1"})

    # --- 4. Exa /contents key parameters & site reachability ---
    ec = "exa-contents"
    add(ec, "exa_cnt:sites_age_neg1", "exa", "contents",
        {"urls": [u for _, u in SITE_TARGETS], "text": {"maxCharacters": 1200}, "maxAgeHours": -1}, 0, 0.008)
    add(ec, "exa_cnt:sites_age_24", "exa", "contents",
        {"urls": [u for k, u in SITE_TARGETS if k in ("bilibili", "tieba", "x", "reddit")],
         "text": {"maxCharacters": 1200}, "maxAgeHours": 24, "livecrawlTimeout": 15000}, 0, 0.004, timeout=180)
    add(ec, "exa_cnt:sites_age_0", "exa", "contents",
        {"urls": [u for k, u in SITE_TARGETS if k in ("bilibili", "tieba")],
         "text": {"maxCharacters": 1200}, "maxAgeHours": 0, "livecrawlTimeout": 15000}, 0, 0.002, timeout=180)
    add(ec, "exa_cnt:billing_multi_types", "exa", "contents",
        {"ids": ["https://docs.python.org/3/library/json.html"],
         "text": {"maxCharacters": 600},
         "highlights": {"query": "JSON encoder", "maxCharacters": 300},
         "summary": {"query": "Main purpose"}}, 0, 0.003)
    add(ec, "exa_cnt:text_options", "exa", "contents",
        {"urls": ["https://docs.python.org/3/library/json.html"],
         "text": {"maxCharacters": 1000, "includeHtmlTags": True, "linkStyle": "citation",
                  "verbosity": "full", "includeSections": ["body"]}}, 0, 0.001)
    add(ec, "exa_cnt:subpages", "exa", "contents",
        {"urls": ["https://docs.python.org/3/"], "subpages": 2, "subpageTarget": "json",
         "text": {"maxCharacters": 500}}, 0, 0.003)
    add(ec, "exa_cnt:subpages_101", "exa", "contents",
        {"urls": ["https://docs.python.org/3/"], "subpages": 101}, 0, 0.0)
    add(ec, "exa_cnt:max_age_721", "exa", "contents",
        {"urls": ["https://docs.python.org/3/library/json.html"],
         "text": {"maxCharacters": 400}, "maxAgeHours": 721}, 0, 0.001)
    add(ec, "exa_cnt:mixed_statuses", "exa", "contents",
        {"urls": ["https://example.com/", "https://example.com/nonexistent-404-probe"],
         "text": {"maxCharacters": 400}, "maxAgeHours": 0, "livecrawlTimeout": 10000}, 0, 0.002)

    return cases


def save_report(out_path, payload):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suite",
        default="all",
        choices=["all", "tavily-search", "tavily-extract", "exa-search", "exa-contents"],
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--delay", type=float, default=0.35)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip cases already recorded in the output JSON and append remaining cases.",
    )
    args = parser.parse_args()

    all_cases = build_cases()
    cases = [c for c in all_cases if args.suite == "all" or c["suite"] == args.suite]

    out_path = args.out_dir / "param_sweep.json"
    existing_records = []
    done_names = set()
    if args.resume and out_path.exists():
        existing_data = json.loads(out_path.read_text(encoding="utf-8"))
        existing_records = list(existing_data.get("records") or [])
        done_names = {r["name"] for r in existing_records if isinstance(r, dict) and "name" in r}
        cases = [c for c in cases if c["name"] not in done_names]

    est_tv = sum(c["est_tavily"] for c in cases)
    est_exa = round(sum(c["est_exa"] for c in cases), 4)
    print(f"Planned cases: {len(cases)} (skipped {len(done_names)}) | est Tavily credits: ~{est_tv} | est Exa: ~USD {est_exa}")
    if args.dry_run:
        for c in cases:
            print(f"  [{c['suite']}] {c['name']} -> {c['provider']}/{c['endpoint']}")
        return

    tkey = api_key("TAVILY_API_KEY")
    ekey = api_key("EXA_API_KEY")

    usage_before = request_json(
        TAVILY_USAGE_URL, None, {"Authorization": f"Bearer {tkey}"}, method="GET"
    )
    print("Tavily usage before:", usage_before.get("http_status"), usage_before.get("data"))

    records = list(existing_records)
    report = {
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "suite": args.suite,
        "tavily_usage_before": usage_before.get("data"),
        "records": records,
    }

    for idx, case in enumerate(cases, 1):
        provider = case["provider"]
        endpoint = case["endpoint"]
        extra = dict(case["extra_headers"])
        if provider == "tavily":
            url = TAVILY_SEARCH_URL if endpoint == "search" else TAVILY_EXTRACT_URL
            headers = {"Authorization": f"Bearer {tkey}", **extra}
            summarizer = summarize_tavily_search if endpoint == "search" else summarize_tavily_extract
        else:
            url = EXA_SEARCH_URL if endpoint == "search" else EXA_CONTENTS_URL
            if extra.pop("__USE_BEARER__", None):
                headers = {"Authorization": f"Bearer {ekey}", **extra}
            else:
                headers = {"x-api-key": ekey, **extra}
            summarizer = summarize_exa_search if endpoint == "search" else summarize_exa_contents

        resp = request_json(url, case["payload"], headers, timeout=case["timeout"])
        summary = summarizer(resp)
        rec = {
            "suite": case["suite"],
            "name": case["name"],
            "provider": provider,
            "endpoint": endpoint,
            "payload": case["payload"],
            "http_status": resp.get("http_status"),
            "elapsed_ms": resp.get("elapsed_ms"),
            "summary": summary,
        }
        if resp.get("error_body"):
            rec["error_body"] = resp["error_body"]
        records.append(rec)
        print(
            f"[{idx:>3}/{len(cases)}] {case['name']:<32} HTTP={str(rec['http_status']):<4} "
            f"{rec['elapsed_ms']:>7}ms"
        )
        save_report(out_path, report)
        if args.delay:
            time.sleep(args.delay)

    usage_after = request_json(
        TAVILY_USAGE_URL, None, {"Authorization": f"Bearer {tkey}"}, method="GET"
    )
    report["tavily_usage_after"] = usage_after.get("data")
    exa_spent = sum(
        (r["summary"].get("cost_total") or (r["summary"].get("costDollars") or {}).get("total") or 0.0)
        for r in records
        if r["provider"] == "exa" and isinstance(r.get("summary"), dict)
    )
    report["exa_observed_usd"] = round(exa_spent, 6)
    save_report(out_path, report)
    print(f"\nSaved -> {out_path}")
    print("Tavily usage after:", usage_after.get("http_status"), usage_after.get("data"))
    print(f"Exa observed total USD: {report['exa_observed_usd']}")


if __name__ == "__main__":
    main()
