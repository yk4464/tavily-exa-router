"""Exa `lite` vs legacy `instant`/`fast` vs `auto`, across three query classes.

Answers the 2026-10-31 routing question: which Exa type is the default for
current events, academic papers, and Chinese-language requests. For each of
6 queries per class and 4 types this measures result count, publication-date
coverage, allowlist hits, latency (3 samples, median), and `costDollars`.
Separately it measures how many results `lite` drops when `contents.highlights`
or `contents.text` is requested, whether `startPublishedDate` windows hold
(including a lower bound set to the current instant), the two documented
`lite` 400s, and Tavily `include_published_date` coverage on the same news
queries.

Quality scoring is deliberately not done here: this script only records the
title/URL/date rows, and the judge runs in the operator's model session so the
script stays stdlib-only. Raw output goes to `search_results/`, which is
git-ignored; the curated numbers live in `references/evidence.md` §7.
"""
import json
import os
import random
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse


def api_key(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"missing environment variable {name}; set it before running this script")
    return value


TAVILY_KEY = api_key("TAVILY_API_KEY")
EXA_KEY = api_key("EXA_API_KEY")

OUT_DIR = Path(__file__).resolve().parent.parent / "search_results"
OUT_FILE = OUT_DIR / "lite_quality.json"

EXA_SEARCH = "https://api.exa.ai/search"
TAVILY_SEARCH = "https://api.tavily.com/search"
EXA_HEADERS = {"x-api-key": EXA_KEY}
TAVILY_HEADERS = {"Authorization": f"Bearer {TAVILY_KEY}"}

MODES = ("lite", "instant", "fast", "auto")
NUM_RESULTS = 8
LATENCY_REPEATS = 3
PERMANENT = {400, 401, 403}
RETRY_STATUSES = {408, 429, 500, 502, 503, 504}

# Six per class. Reused from tests/batch_compare.py, tests/mode_quality_test.py,
# tests/search_compare.py and tests/community_test.py where a label matches;
# the rest cover the same shapes. Classes are judged separately. The first
# tuple element is the class label (same as the dict key), kept in each record
# for parity with the older scripts; `query` is the unique key.
QUERIES = {
    "news": [
        ("news", "AI chip export controls latest"),
        ("news", "open source model releases this week"),
        ("news", "latest AI model releases October 2026"),
        ("news", "US government shutdown latest"),
        ("news", "Nvidia earnings latest quarter results"),
        ("news", "AI regulation policy news"),
    ],
    "academic": [
        ("academic", "retrieval augmented generation hallucination reduction papers"),
        ("academic", "mamba state space models survey"),
        ("academic", "transformer attention efficiency survey"),
        ("academic", "diffusion language models paper"),
        ("academic", "RLHF reward hacking papers"),
        ("academic", "graph neural network drug discovery review"),
    ],
    "chinese": [
        ("chinese", "2026年大模型API价格对比"),
        ("chinese", "Redis 分布式锁 实现方案"),
        ("chinese", "新能源汽车 补贴政策 2026"),
        ("chinese", "Rust 生产环境使用经验 踩坑"),
        ("chinese", "国产数据库 分布式事务 方案对比"),
        ("chinese", "个人养老金 账户 政策 最新"),
    ],
}

# Same lists as tests/comprehensive_benchmark.py, so hit counts are comparable
# with references/evidence.md §1/§5. They are coarse for academic and Chinese
# sources; the blind judge, not these lists, decides quality.
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


def domain(url):
    return urlparse(url).netloc.replace("www.", "")


def tier(url):
    d = domain(url)
    if d in AUTHORITATIVE_DOMAINS:
        return "auth"
    if d in COMMUNITY_DOMAINS:
        return "comm"
    return "other"


def post(url, payload, headers, timeout=120, retries=2):
    """POST JSON, retrying rate limits, 5xx, and transport errors.

    400/401/403 are permanent: retrying re-sends the same rejected request.
    Returns (status, data, error): `error` carries the first 800 characters of
    a non-2xx body so the 400 field names stay inspectable.
    """
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url, data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json", **headers},
                method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, json.load(r), None
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "ignore")[:800]
            if exc.code in PERMANENT or exc.code not in RETRY_STATUSES or attempt == retries:
                return exc.code, None, body
            time.sleep(4 * (attempt + 1))
        except Exception as exc:  # noqa: BLE001 - transport-level: retry
            if attempt == retries:
                return None, None, f"{type(exc).__name__}: {exc}"
            time.sleep(4 * (attempt + 1))
    return None, None, "retry loop exhausted"


def date_value(result):
    """Exa returns ISO `publishedDate`; Tavily returns an RFC 2822
    `published_date` string. Normalize both to YYYY-MM-DD so a stored date
    is comparable across providers (and not a sliced weekday name)."""
    value = result.get("publishedDate") or result.get("published_date")
    if not value:
        return None
    if isinstance(value, str) and "," in value:
        try:
            return parsedate_to_datetime(value).date().isoformat()
        except (TypeError, ValueError):
            pass
    return str(value)[:10]


def row(result):
    url = result.get("url") or ""
    return {
        "title": (result.get("title") or "")[:160],
        "url": url,
        "domain": domain(url),
        "tier": tier(url),
        # Exa uses `publishedDate`; Tavily uses `published_date` (RFC 2822).
        "date": date_value(result),
        "author": (result.get("author") or None),
        "score": result.get("score"),
        # Content presence distinguishes a cached-but-empty copy from a
        # result the API kept without serving content.
        "text_chars": len(result.get("text") or ""),
        "highlights": len(result.get("highlights") or []),
    }


def exa_call(mode, query, contents=None, extra=None):
    payload = {"query": query, "numResults": NUM_RESULTS, "type": mode}
    if contents:
        payload["contents"] = contents
    if extra:
        payload.update(extra)
    started = time.perf_counter()
    status, data, error = post(EXA_SEARCH, payload, EXA_HEADERS)
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    results = [row(item) for item in (data or {}).get("results", [])]
    cost = None
    if isinstance(data, dict):
        cd = data.get("costDollars")
        if isinstance(cd, dict):
            cost = cd.get("total")
        elif isinstance(cd, (int, float)):
            cost = cd
    return {
        "status": status,
        "ms": elapsed_ms,
        "count": len(results),
        "cost": cost,
        "results": results,
        "error": error,
    }


def summarize(records):
    """Per (class, mode): count, dated share, allowlist hits, latency, cost."""
    table = []
    for cls in QUERIES:
        for mode in MODES:
            rows = [r for r in records
                    if r["class"] == cls and r["mode"] == mode and r["status"] == 200]
            if not rows:
                table.append({"class": cls, "mode": mode, "calls": 0})
                continue
            first = [r for r in rows if r.get("repeat") == 0] or rows
            flat = [item for r in first for item in r["results"]]
            latencies = [r["ms"] for r in rows]
            costs = [r["cost"] for r in first if isinstance(r["cost"], (int, float))]
            table.append({
                "class": cls,
                "mode": mode,
                "calls": len(rows),
                "results_per_query": round(statistics.mean(r["count"] for r in first), 2),
                "dated_share": round(
                    sum(1 for item in flat if item["date"]) / len(flat), 3) if flat else 0,
                "auth_hits": sum(1 for item in flat if item["tier"] == "auth"),
                "comm_hits": sum(1 for item in flat if item["tier"] == "comm"),
                "median_ms": round(statistics.median(latencies)),
                "cost_per_query": round(statistics.median(costs), 6) if costs else None,
            })
    return table


def jaccard(a, b):
    sa, sb = set(a), set(b)
    return round(len(sa & sb) / len(sa | sb), 3) if sa | sb else None


def bootstrap_ci(pairs, resamples=10000, seed=20261031):
    """95% percentile CI of the mean paired difference (values are per query)."""
    if not pairs:
        return None
    rng = random.Random(seed)
    means = []
    n = len(pairs)
    for _ in range(resamples):
        means.append(sum(pairs[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return [round(means[int(0.025 * resamples)], 3),
            round(means[int(0.975 * resamples)], 3)]


def fmt_date(d):
    return d[:10] if d else ""


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    artifact = {
        "meta": {
            "date": started.strftime("%Y-%m-%d"),
            "started_utc": started.isoformat(timespec="seconds"),
            "egress": "single local Windows workstation",
            "python": sys.version.split()[0],
            "num_results": NUM_RESULTS,
            "latency_repeats": LATENCY_REPEATS,
            "endpoint": EXA_SEARCH,
        },
        "quality": [],
        "contents": [],
        "date_windows": [],
        "lite_errors": [],
        "tavily": [],
        "summary": [],
    }

    # Phase 1: plain search, sequential, 3 repeats per query/type. Sequential
    # and order-rotated so the latency samples are not shaped by thread pool
    # contention; repeat 0 doubles as the quality row.
    rng = random.Random(20261031)
    total = sum(len(v) for v in QUERIES.values()) * len(MODES) * LATENCY_REPEATS
    done = 0
    for cls, queries in QUERIES.items():
        for qlabel, query in queries:
            for repeat in range(LATENCY_REPEATS):
                order = list(MODES)
                # Rotate which type goes first, so no type always pays the
                # connection warm-up or always runs last.
                shift = (repeat + rng.randrange(len(MODES))) % len(MODES)
                order = order[shift:] + order[:shift]
                for mode in order:
                    result = exa_call(mode, query)
                    artifact["quality"].append({
                        "class": cls, "qlabel": qlabel, "query": query,
                        "mode": mode, "repeat": repeat, **result,
                    })
                    done += 1
                    if done % 24 == 0:
                        print(f"  plain calls {done}/{total}", flush=True)
                    time.sleep(0.1)

    # Phase 2: contents behavior. `lite` only serves cached copies and omits
    # results without one when text/highlights are asked for. `instant` with
    # the same contents is the gate control (did `lite` return fewer results
    # than `instant`?); `auto` + highlights shows whether any drop is
    # specific to `lite`.
    print("contents drop checks", flush=True)
    contents_jobs = []
    for cls, queries in QUERIES.items():
        for qlabel, query in queries:
            contents_jobs += [
                ("lite", "highlights", query, cls, qlabel,
                 {"highlights": {"maxCharacters": 800}}),
                ("lite", "text", query, cls, qlabel,
                 {"text": {"maxCharacters": 1200}}),
                ("instant", "highlights", query, cls, qlabel,
                 {"highlights": {"maxCharacters": 800}}),
                ("instant", "text", query, cls, qlabel,
                 {"text": {"maxCharacters": 1200}}),
                ("auto", "highlights", query, cls, qlabel,
                 {"highlights": {"maxCharacters": 800}}),
            ]

    def run_contents(job):
        mode, ctype, query, cls, qlabel, contents = job
        result = exa_call(mode, query, contents=contents)
        return {"class": cls, "qlabel": qlabel, "query": query, "mode": mode,
                "contents": ctype, **result}

    with ThreadPoolExecutor(max_workers=5) as pool:
        artifact["contents"] = list(pool.map(run_contents, contents_jobs))

    # Phase 3: startPublishedDate windows. One news query (7-day window,
    # lower bound = now minus 7 days) and one academic/Chinese query per
    # class, plus the counterexample the docs warn about: a lower bound set
    # to the current instant.
    now = datetime.now(timezone.utc)
    week = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    instant = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    window_jobs = []
    for cls, queries in QUERIES.items():
        qlabel, query = queries[0]
        for mode in ("lite", "instant", "auto"):
            window_jobs.append({
                "class": cls, "qlabel": qlabel, "query": query, "mode": mode,
                "window": "7d", "start": week,
            })
        window_jobs.append({
            "class": cls, "qlabel": qlabel, "query": query, "mode": "lite",
            "window": "now", "start": instant,
        })
        window_jobs.append({
            "class": cls, "qlabel": qlabel, "query": query, "mode": "auto",
            "window": "now", "start": instant,
        })

    def run_window(job):
        result = exa_call(job["mode"], job["query"],
                          extra={"startPublishedDate": job["start"]})
        dates = [item["date"] for item in result["results"] if item["date"]]
        out_of_window = sum(1 for d in dates if d < job["start"][:10])
        return {**job, **result,
                "dated": len(dates), "undated": result["count"] - len(dates),
                "out_of_window": out_of_window,
                "min_date": min(dates) if dates else None,
                "max_date": max(dates) if dates else None}

    with ThreadPoolExecutor(max_workers=5) as pool:
        artifact["date_windows"] = list(pool.map(run_window, window_jobs))

    # Phase 4: the two documented `lite` rejections. A 400 must name the
    # offending field; that is the fact being checked, not just the status.
    print("lite 400 checks", flush=True)
    rejections = [
        ("outputSchema", {"outputSchema": {
            "type": "object",
            "properties": {"answer": {"type": "string"}},
        }}),
        ("contents.summary", {"contents": {"summary": {"query": "key points"}}}),
    ]
    for name, extra in rejections:
        result = exa_call("lite", "python requests library", extra=extra)
        artifact["lite_errors"].append({"case": name, **result})

    # Phase 5: Tavily include_published_date on the same six news queries,
    # with a no-flag control on the first two.
    print("tavily date coverage", flush=True)

    def run_tavily(job):
        qlabel, query, flag, topic = job
        payload = {"query": query, "max_results": NUM_RESULTS,
                   "search_depth": "basic", "topic": topic,
                   "include_usage": True}
        if flag:
            payload["include_published_date"] = True
        started = time.perf_counter()
        status, data, error = post(TAVILY_SEARCH, payload, TAVILY_HEADERS)
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        results = [row(item) for item in (data or {}).get("results", [])]
        usage = (data or {}).get("usage") or {}
        return {
            "class": "news", "qlabel": qlabel, "query": query, "topic": topic,
            "include_published_date": flag, "status": status, "ms": elapsed_ms,
            "count": len(results), "dated": sum(1 for item in results if item["date"]),
            "credits": usage.get("credits"), "results": results, "error": error,
        }

    tavily_jobs = [(qlabel, query, True, "general")
                   for qlabel, query in QUERIES["news"]]
    tavily_jobs += [(qlabel, query, False, "general")
                    for qlabel, query in QUERIES["news"][:2]]
    # `topic: news` turns the flag on automatically; one probe documents it.
    tavily_jobs.append(("news-topic", QUERIES["news"][0][1], False, "news"))
    with ThreadPoolExecutor(max_workers=4) as pool:
        artifact["tavily"] = list(pool.map(run_tavily, tavily_jobs))

    # Derived views used by the report and by the blind judge.
    artifact["summary"] = summarize(artifact["quality"])
    plain = {(r["class"], r["query"], r["mode"]): r for r in artifact["quality"]
             if r.get("repeat") == 0}

    def plain_results(cls, query, mode):
        return (plain.get((cls, query, mode)) or {}).get("results") or []

    for mode in MODES:
        pairs = []
        for cls in QUERIES:
            for _, query in QUERIES[cls]:
                a = {i["url"] for i in plain_results(cls, query, "lite")}
                b = {i["url"] for i in plain_results(cls, query, mode)}
                pairs.append(jaccard(a, b))
        known = [p for p in pairs if p is not None]
        artifact.setdefault("jaccard", {})[f"lite_vs_{mode}"] = {
            "per_query": pairs,
            "mean": round(statistics.mean(known), 3) if known else None,
        }

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(artifact, f, ensure_ascii=False, indent=1)

    # Console summary: the table the report quotes.
    print("\nclass   mode      calls  res/q  dated  auth  comm  median_ms  cost/q")
    for row_ in artifact["summary"]:
        if not row_.get("calls"):
            print(f"{row_['class']:<7} {row_['mode']:<9} 0")
            continue
        print(f"{row_['class']:<7} {row_['mode']:<9} {row_['calls']:<5}"
              f" {row_['results_per_query']:<6} {row_['dated_share']:<6}"
              f" {row_['auth_hits']:<5} {row_['comm_hits']:<5}"
              f" {row_['median_ms']:<10} {row_['cost_per_query']}")

    print("\ncontents gate (lite vs instant with the same contents):")
    for cls in QUERIES:
        for ctype in ("highlights", "text"):
            drops, overlaps = [], []
            for _, query in QUERIES[cls]:
                base_urls = [i["url"] for i in plain_results(cls, query, "lite")]
                lite_rec = next((r for r in artifact["contents"]
                                 if r["class"] == cls and r["query"] == query
                                 and r["mode"] == "lite" and r["contents"] == ctype
                                 and r["status"] == 200), None)
                inst_rec = next((r for r in artifact["contents"]
                                 if r["class"] == cls and r["query"] == query
                                 and r["mode"] == "instant" and r["contents"] == ctype
                                 and r["status"] == 200), None)
                if lite_rec and inst_rec and inst_rec["count"]:
                    drops.append(1 - lite_rec["count"] / inst_rec["count"])
                if lite_rec:
                    overlaps.append(jaccard(base_urls, [i["url"] for i in lite_rec["results"]]))
            known_overlaps = [o for o in overlaps if o is not None]
            if drops:
                print(f"  {cls:<7} +{ctype:<10}"
                      f" count drop vs instant {statistics.mean(drops):.0%}"
                      f" (per query {[round(d, 2) for d in drops]})"
                      f"  URL overlap vs plain "
                      f"{statistics.mean(known_overlaps) if known_overlaps else float('nan'):.2f}")

    print("\nlite 400s:")
    for item in artifact["lite_errors"]:
        print(f"  {item['case']}: HTTP {item['status']} {item['error']}")

    print("\nTavily include_published_date:")
    for item in artifact["tavily"]:
        print(f"  flag={item['include_published_date']} "
              f"{item['dated']}/{item['count']} dated  {item['query'][:48]}")
    print(f"\nsaved -> {OUT_FILE}")


if __name__ == "__main__":
    main()
