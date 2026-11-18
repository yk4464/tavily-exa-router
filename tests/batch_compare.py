"""Phase 3c+3d: batch comparison over 20 categorized queries + link validity + cost.

Concurrency: 4 workers for API calls, 10 for HTTP spot-checks.
"""
import argparse
import json
import math
import os
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse


def api_key(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"missing environment variable {name}; set it before running this script")
    return value


TAVILY_KEY = None
EXA_KEY = None

OUT_DIR = Path(__file__).resolve().parent.parent / "search_results"
TAVILY_TOPIC = "general"
EXA_TYPE = "lite"

QUERIES = [
    ("factual", "height of Mount Everest in meters"),
    ("factual", "current CEO of OpenAI"),
    ("news", "AI chip export controls latest"),
    ("news", "open source model releases this week"),
    ("zh-tech", "Redis 分布式锁 实现方案"),
    ("zh-news", "新能源汽车 补贴政策 2026"),
    ("longtail", "how to fix kafka consumer lag rebalancing loop"),
    ("longtail", "postgres partition pruning not working slow query"),
    ("niche", "embedded rust no_std allocator design"),
    ("niche", "JVM ZGC colored pointers implementation"),
    ("comparison", "turborepo vs nx monorepo"),
    ("comparison", "clickhouse vs duckdb analytics benchmark"),
    ("entity", "Dario Amodei background education"),
    ("entity", "Exa AI company founders funding"),
    ("academic", "retrieval augmented generation hallucination reduction papers"),
    ("academic", "mamba state space models survey"),
    ("community", "vite vs webpack developer opinions"),
    ("howto", "deploy fastapi kubernetes best practices"),
    ("misc", "best ramen shops Tokyo 2026"),
    ("product", "sony wh-1000xm6 review noise cancelling"),
]


def post_json(url, payload, headers, timeout=120, retries=2):
    # 400/401/403 are permanent: retrying spends calls and wall-clock to
    # reach the same failure. SKILL.md says a 400 means fix the parameters,
    # not retry. Only 429/5xx and transport errors are worth another attempt.
    permanent = {400, 401, 403}
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url, data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json", **headers}, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as exc:
            if exc.code in permanent or attempt == retries:
                raise
            time.sleep(4 * (attempt + 1))
        except Exception:  # noqa: BLE001 - transport-level: worth retrying
            if attempt == retries:
                raise
            time.sleep(4 * (attempt + 1))


def tavily(q):
    d = post_json("https://api.tavily.com/search",
                  {"query": q, "max_results": 8, "search_depth": "basic",
                   "topic": TAVILY_TOPIC, "include_usage": True},
                  {"Authorization": f"Bearer {TAVILY_KEY}"})
    # Read the real date field; Tavily only populates published_date in some
    # modes, and the output row records TAVILY_TOPIC so the "dated" tally is
    # interpretable rather than a property of this collector.
    return [{"u": r["url"], "t": (r.get("title") or "")[:80],
             "d": r.get("published_date"),
             "s": r.get("score")} for r in d.get("results", [])], d.get("usage")


def exa(q):
    d = post_json("https://api.exa.ai/search",
                  {"query": q, "numResults": 8, "type": EXA_TYPE},
                  {"x-api-key": EXA_KEY})
    return [{"u": r["url"], "t": (r.get("title") or "")[:80],
             "d": (r.get("publishedDate") or "")[:10], "s": None}
            for r in d.get("results", [])], d.get("costDollars")


def run_pair(indexed_item):
    index, item = indexed_item
    cat, q = item
    row = {"cat": cat, "query": q}
    providers = (("tavily", tavily), ("exa", exa))
    if index % 2:
        providers = tuple(reversed(providers))
    for name, fn in providers:
        started = time.perf_counter()
        try:
            results, cost = fn(q)
            row[name] = {"results": results, "cost": cost, "error": None,
                         "elapsed_ms": round((time.perf_counter() - started) * 1000)}
        except Exception as exc:  # noqa: BLE001
            row[name] = {"results": [], "cost": None, "error": str(exc),
                         "elapsed_ms": round((time.perf_counter() - started) * 1000)}
    row["tavily"]["topic"] = TAVILY_TOPIC
    row["exa"]["type"] = EXA_TYPE
    return row


def usage_value(service, value):
    if not isinstance(value, dict):
        return value
    return value.get("credits") if service == "tavily" else value.get("total")


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1))]


def domain(u):
    return urlparse(u).netloc.replace("www.", "")


COMMUNITY = {"reddit.com", "news.ycombinator.com", "stackoverflow.com", "zhihu.com",
             "zhuanlan.zhihu.com", "v2ex.com", "juejin.cn", "cnblogs.com",
             "segmentfault.com", "dev.to", "medium.com", "substack.com", "quora.com"}
AUTHORITATIVE = {"arxiv.org", "github.com", "reuters.com", "bloomberg.com", "apnews.com",
                 "nature.com", "acm.org", "ieee.org", "docs.python.org", "rust-lang.org",
                 "postgresql.org", "kafka.apache.org", "news.qq.com", "people.com.cn",
                 "gov.cn", "mp.weixin.qq.com"}


def tier(d):
    if d in AUTHORITATIVE:
        return "auth"
    if d in COMMUNITY:
        return "comm"
    return "other"


def http_check(url):
    try:
        req = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=8) as r:
            return url, r.status
    except urllib.error.HTTPError as e:
        if e.code in (403, 405, 501):  # HEAD rejected -> try GET
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=8) as r:
                    return url, r.status
            except Exception as e2:  # noqa: BLE001
                return url, getattr(e2, "code", "err")
        return url, e.code
    except Exception as e:  # noqa: BLE001
        return url, getattr(e, "code", "err")


def main():
    global TAVILY_KEY, EXA_KEY, OUT_DIR, EXA_TYPE
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR, help="directory for raw JSON output")
    parser.add_argument("--exa-type", default=EXA_TYPE, help="Exa search type (default: lite)")
    args = parser.parse_args()

    TAVILY_KEY = api_key("TAVILY_API_KEY")
    EXA_KEY = api_key("EXA_API_KEY")
    OUT_DIR = args.out_dir
    EXA_TYPE = args.exa_type

    # Fail on an unwritable output directory before spending any API calls.
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=4) as ex:
        rows = list(ex.map(run_pair, enumerate(QUERIES)))

    # HTTP spot-check: up to 3 URLs per query per service
    check_urls = []
    for row in rows:
        for svc in ("tavily", "exa"):
            check_urls += [r["u"] for r in row[svc]["results"][:3]]
    with ThreadPoolExecutor(max_workers=10) as ex:
        statuses = dict(ex.map(http_check, check_urls))

    output = OUT_DIR / "batch_compare.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump({"rows": rows, "http_status": statuses}, f, ensure_ascii=False, indent=1)

    # ---- report ----
    print(f"batch done in {time.time() - t0:.0f}s\n")
    print(f"{'category':<11}{'query':<42}| T: n/comm/auth/dated | E: n/comm/auth/dated")
    print("-" * 130)
    tot = {"tavily": {"n": 0, "comm": 0, "auth": 0, "dated": 0, "err": 0},
           "exa": {"n": 0, "comm": 0, "auth": 0, "dated": 0, "err": 0}}
    costs = {"tavily": [], "exa": []}
    latencies = {"tavily": [], "exa": []}
    for row in rows:
        line = f"{row['cat']:<11}{row['query'][:40]:<42}"
        for svc in ("tavily", "exa"):
            rs = row[svc]["results"]
            if row[svc]["error"]:
                tot[svc]["err"] += 1
                line += f"| {'ERR':^22}"
                continue
            latencies[svc].append(row[svc]["elapsed_ms"])
            doms = [domain(r["u"]) for r in rs]
            n, comm, auth = len(rs), sum(tier(d) == "comm" for d in doms), sum(tier(d) == "auth" for d in doms)
            dated = sum(1 for r in rs if r.get("d"))
            tot[svc].update({"n": tot[svc]["n"] + n, "comm": tot[svc]["comm"] + comm,
                             "auth": tot[svc]["auth"] + auth, "dated": tot[svc]["dated"] + dated})
            line += f"| {n:>2}/{comm}/{auth}/{dated:<8}"
            if row[svc]["cost"] is not None:
                value = usage_value(svc, row[svc]["cost"])
                if isinstance(value, (int, float)):
                    costs[svc].append(value)
        print(line)

    print("\n== totals (out of 20 queries) ==")
    for svc in ("tavily", "exa"):
        t = tot[svc]
        print(f"  {svc:<7} results={t['n']} community={t['comm']} authoritative={t['auth']} "
              f"dated={t['dated']} errors={t['err']}")

    # overlap: same domain appearing in both result sets per query
    overlaps = []
    for row in rows:
        if row["tavily"]["error"] or row["exa"]["error"]:
            continue
        dt = {domain(r["u"]) for r in row["tavily"]["results"]}
        de = {domain(r["u"]) for r in row["exa"]["results"]}
        if dt or de:
            overlaps.append(len(dt & de) / len(dt | de))
    # Guard every aggregate: when all queries fail, overlaps and every latency
    # list are empty, and statistics.median([])/min([]) would raise and discard
    # the console summary exactly when diagnostics matter most.
    avg_overlap = f"{sum(overlaps) / len(overlaps):.2f}" if overlaps else "N/A"
    print(f"\n== domain overlap per query (Jaccard, avg): {avg_overlap}")

    print("\n== API latency (20 mixed queries, concurrent run) ==")
    for svc in ("tavily", "exa"):
        vals = latencies[svc]
        if not vals:
            print(f"  {svc:<7} median=N/A p95=N/A min=N/A max=N/A (all requests failed)")
            continue
        print(f"  {svc:<7} median={statistics.median(vals):.0f}ms "
              f"p95={percentile(vals, 0.95):.0f}ms min={min(vals):.0f}ms max={max(vals):.0f}ms")

    ok = sum(1 for s in statuses.values() if s == 200)
    bad = {u: s for u, s in statuses.items() if s != 200}
    print(f"== link validity: {ok}/{len(statuses)} returned 200; failures: {len(bad)}")
    for u, s in list(bad.items())[:8]:
        print(f"   {s} {u[:80]}")

    print("\n== per-query cost ==")
    for svc in ("tavily", "exa"):
        vals = costs[svc]
        if vals and svc == "exa":
            print(f"  exa  costDollars avg={sum(vals) / len(vals):.4f} max={max(vals):.4f} over {len(vals)} queries")
        elif vals:
            print(f"  tavily credits avg={sum(vals) / len(vals):.2f} max={max(vals):.0f} over {len(vals)} queries")

    print(f"\nsaved -> {output}")


if __name__ == "__main__":
    main()
