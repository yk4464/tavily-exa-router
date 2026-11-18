"""Community-content search comparison: Tavily vs Exa.

Two community-flavored queries (EN + CN), plain mode on both services,
plus Exa's category="personal site" variant for reference.
"""
import json
import os
import urllib.request
from urllib.parse import urlparse


def api_key(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"missing environment variable {name}; set it before running this script")
    return value


TAVILY_KEY = None
EXA_KEY = None


def post(url, payload, headers):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def tavily(query):
    return post("https://api.tavily.com/search",
                {"query": query, "max_results": 8, "search_depth": "basic"},
                {"Authorization": f"Bearer {TAVILY_KEY}"})["results"]


def exa(query, category=None, exa_type="lite"):
    payload = {"query": query, "numResults": 8, "type": exa_type,
               "contents": {"text": {"maxCharacters": 200}}}
    if category:
        payload["category"] = category
    return post("https://api.exa.ai/search", payload,
                {"x-api-key": EXA_KEY})["results"]


def domain(url):
    return urlparse(url).netloc.replace("www.", "")


def trunc(s, n=60):
    s = (s or "").replace("\n", " ").strip()
    return s[: n - 1] + "…" if len(s) > n else s


# heuristics: known community UGC sites
COMMUNITY = {"reddit.com", "news.ycombinator.com", "stackoverflow.com",
             "stackexchange.com", "zhihu.com", "zhuanlan.zhihu.com", "v2ex.com",
             "juejin.cn", "cnblogs.com", "segmentfault.com", "dev.to",
             "medium.com", "substack.com", "hashnode.dev", "oschina.net",
             "linux.do", "discord.com", "github.com"}


def show(name, results):
    comm = sum(1 for r in results if domain(r.get("url", "")) in COMMUNITY)
    print(f"\n--- {name}: {comm}/{len(results)} results from community sites")
    for i, r in enumerate(results, 1):
        d = domain(r.get("url", ""))
        mark = "[C]" if d in COMMUNITY else "   "
        print(f"  {i}.{mark} [{d}] {trunc(r.get('title'), 55)}")


def safe_show(name, fn):
    try:
        show(name, fn())
    except Exception as exc:  # noqa: BLE001
        print(f"\n--- {name}: ERROR {exc}")


def main():
    global TAVILY_KEY, EXA_KEY
    TAVILY_KEY = api_key("TAVILY_API_KEY")
    EXA_KEY = api_key("EXA_API_KEY")

    for label, q in [
        ("EN-community", "tailwind css criticism real developer experience"),
        ("CN-community", "Rust 生产环境使用经验 踩坑"),
    ]:
        print(f"\n{'=' * 78}\nQUERY [{label}]: {q}")
        safe_show("Tavily basic", lambda q=q: tavily(q))
        safe_show("Exa lite", lambda q=q: exa(q, exa_type="lite"))
        safe_show("Exa deep", lambda q=q: exa(q, exa_type="deep"))

    # Exa's dedicated community-ish category for reference
    print(f"\n{'=' * 78}\n[Exa category='personal site' variant]")
    safe_show(
        "Exa lite + personal site",
        lambda: exa("tailwind css criticism real developer experience",
                    category="personal site", exa_type="lite"),
    )


if __name__ == "__main__":
    main()
