"""Phase 3c+3d: batch comparison over 20 categorized queries + link validity + cost.

Concurrency: 6 workers for API calls, 10 for HTTP spot-checks.
"""
import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

TAVILY_KEY = os.environ["TAVILY_API_KEY"]
EXA_KEY = os.environ["EXA_API_KEY"]

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
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url, data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json", **headers}, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except Exception:  # noqa: BLE001
            if attempt == retries:
                raise
            time.sleep(4 * (attempt + 1))


def tavily(q):
    d = post_json("https://api.tavily.com/search",
                  {"query": q, "max_results": 8, "search_depth": "basic",
                   "include_usage": True},
                  {"Authorization": f"Bearer {TAVILY_KEY}"})
    return [{"u": r["url"], "t": (r.get("title") or "")[:80], "d": None,
             "s": r.get("score")} for r in d.get("results", [])], d.get("usage")


def exa(q):
    d = post_json("https://api.exa.ai/search",
                  {"query": q, "numResults": 8, "type": "auto"},
                  {"x-api-key": EXA_KEY})
    return [{"u": r["url"], "t": (r.get("title") or "")[:80],
             "d": (r.get("publishedDate") or "")[:10], "s": None}
            for r in d.get("results", [])], d.get("costDollars")


def run_pair(item):
    cat, q = item
    row = {"cat": cat, "query": q}
    for name, fn in (("tavily", tavily), ("exa", exa)):
        try:
            results, cost = fn(q)
            row[name] = {"results": results, "cost": cost, "error": None}
        except Exception as exc:  # noqa: BLE001
            row[name] = {"results": [], "cost": None, "error": str(exc)}
    return row


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


if __name__ == "__main__":
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=6) as ex:
        rows = list(ex.map(run_pair, QUERIES))

    # HTTP spot-check: up to 3 URLs per query per service
    check_urls = []
    for row in rows:
        for svc in ("tavily", "exa"):
            check_urls += [r["u"] for r in row[svc]["results"][:3]]
    with ThreadPoolExecutor(max_workers=10) as ex:
        statuses = dict(ex.map(http_check, check_urls))

    with open("search_results/batch_compare.json", "w", encoding="utf-8") as f:
        json.dump({"rows": rows, "http_status": statuses}, f, ensure_ascii=False, indent=1)

    # ---- report ----
    print(f"batch done in {time.time() - t0:.0f}s\n")
    print(f"{'category':<11}{'query':<42}| T: n/comm/auth/dated | E: n/comm/auth/dated")
    print("-" * 130)
    tot = {"tavily": {"n": 0, "comm": 0, "auth": 0, "dated": 0, "err": 0},
           "exa": {"n": 0, "comm": 0, "auth": 0, "dated": 0, "err": 0}}
    costs = {"tavily": [], "exa": []}
    for row in rows:
        line = f"{row['cat']:<11}{row['query'][:40]:<42}"
        for svc in ("tavily", "exa"):
            rs = row[svc]["results"]
            if row[svc]["error"]:
                tot[svc]["err"] += 1
                line += f"| {'ERR':^22}"
                continue
            doms = [domain(r["u"]) for r in rs]
            n, comm, auth = len(rs), sum(tier(d) == "comm" for d in doms), sum(tier(d) == "auth" for d in doms)
            dated = sum(1 for r in rs if r.get("d"))
            tot[svc].update({"n": tot[svc]["n"] + n, "comm": tot[svc]["comm"] + comm,
                             "auth": tot[svc]["auth"] + auth, "dated": tot[svc]["dated"] + dated})
            line += f"| {n:>2}/{comm}/{auth}/{dated:<8}"
            if row[svc]["cost"] is not None:
                costs[svc].append(row[svc]["cost"])
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
    print(f"\n== domain overlap per query (Jaccard, avg): {sum(overlaps) / len(overlaps):.2f}")

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
            print(f"  tavily usage samples: {json.dumps(vals[:3])}")
