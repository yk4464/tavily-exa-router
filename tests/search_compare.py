"""Fair side-by-side comparison of Tavily vs Exa search APIs.

Runs identical queries against both services with equivalent parameters,
saves raw JSON, and prints a compact per-result summary for analysis.
"""
import json
import os
import urllib.request
from urllib.parse import urlparse

TAVILY_KEY = os.environ["TAVILY_API_KEY"]
EXA_KEY = os.environ["EXA_API_KEY"]

QUERIES = [
    ("chinese", "2026年国产大模型开源最新进展"),
    ("technical", "SQLite vs Postgres tradeoffs for local-first applications"),
    ("freshness", "latest AI model releases August 2026"),
]


def post(url, payload, headers):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def tavily_search(query):
    return post(
        "https://api.tavily.com/search",
        {
            "query": query,
            "max_results": 8,
            "search_depth": "basic",
            "include_answer": False,
        },
        {"Authorization": f"Bearer {TAVILY_KEY}"},
    )


def exa_search(query):
    return post(
        "https://api.exa.ai/search",
        {
            "query": query,
            "numResults": 8,
            "contents": {"text": {"maxCharacters": 260}},
            "type": "auto",
        },
        {"x-api-key": EXA_KEY},
    )


def domain(url):
    return urlparse(url).netloc.replace("www.", "")


def trunc(s, n=70):
    s = (s or "").replace("\n", " ").strip()
    return s[: n - 1] + "…" if len(s) > n else s


os.makedirs("search_results", exist_ok=True)

for label, q in QUERIES:
    print(f"\n{'=' * 80}\nQUERY [{label}]: {q}\n{'=' * 80}")
    for name, fn in (("TAVILY", tavily_search), ("EXA", exa_search)):
        try:
            data = fn(q)
        except Exception as exc:  # noqa: BLE001
            print(f"\n--- {name} ERROR: {exc}")
            continue
        with open(f"search_results/{label}_{name.lower()}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        results = data.get("results", [])
        print(f"\n--- {name} ({len(results)} results, response_time={data.get('response_time', 'n/a')})")
        for i, r in enumerate(results, 1):
            title = trunc(r.get("title"), 58)
            pub = (r.get("publishedDate") or r.get("published_date") or "")[:10]
            score = r.get("score") or r.get("relevance_score")
            score_s = f"{score:.3f}" if isinstance(score, (int, float)) else "  -  "
            snippet = r.get("text") or r.get("content") or ""
            print(f"  {i}. [{domain(r.get('url',''))}] {title} | {pub or 'no-date'} | {score_s}")
            print(f"     {trunc(snippet, 96)}")
