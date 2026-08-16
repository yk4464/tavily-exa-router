"""Phase 3a: search-mode quality comparison.

Same 4 queries through Tavily {basic, fast, advanced} and
Exa {instant, fast, auto, deep-lite}. Results saved for manual quality review.
"""
import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

TAVILY_KEY = os.environ["TAVILY_API_KEY"]
EXA_KEY = os.environ["EXA_API_KEY"]


def post(url, payload, headers, timeout=240, retries=2):
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url, data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json", **headers}, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except Exception as exc:  # noqa: BLE001
            if attempt == retries:
                raise
            time.sleep(4 * (attempt + 1))


QUERIES = [
    ("research", "best vector database 2026 comparison"),
    ("technical", "how to prevent prompt injection in production agents"),
    ("chinese", "2026年大模型API价格对比"),
    ("factual", "current CEO of Anthropic"),
]

jobs = [("tavily", m, ql, q) for ql, q in QUERIES for m in ("basic", "fast", "advanced")]
jobs += [("exa", m, ql, q) for ql, q in QUERIES for m in ("instant", "fast", "auto", "deep-lite")]


def run(job):
    svc, mode, qlabel, q = job
    t0 = time.perf_counter()
    try:
        if svc == "tavily":
            data = post("https://api.tavily.com/search",
                        {"query": q, "max_results": 5, "search_depth": mode,
                         "include_usage": True},
                        {"Authorization": f"Bearer {TAVILY_KEY}"})
            results = [{"t": (r.get("title") or "")[:70], "u": r.get("url", ""),
                        "s": r.get("score")} for r in data.get("results", [])]
            usage = data.get("usage")
        else:
            data = post("https://api.exa.ai/search",
                        {"query": q, "numResults": 5, "type": mode},
                        {"x-api-key": EXA_KEY})
            results = [{"t": (r.get("title") or "")[:70], "u": r.get("url", ""),
                        "d": (r.get("publishedDate") or "")[:10]} for r in data.get("results", [])]
            usage = {"costDollars": data.get("costDollars")}
        return {"svc": svc, "mode": mode, "q": qlabel, "secs": round(time.perf_counter() - t0, 1),
                "results": results, "usage": usage, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"svc": svc, "mode": mode, "q": qlabel,
                "secs": round(time.perf_counter() - t0, 1),
                "results": [], "usage": None, "error": str(exc)}


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=5) as ex:
        out = list(ex.map(run, jobs))
    os.makedirs("search_results", exist_ok=True)
    with open("search_results/mode_quality.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    for svc in ("tavily", "exa"):
        print(f"\n{'#' * 70}\n# {svc.upper()}\n{'#' * 70}")
        for qlabel, q in QUERIES:
            print(f"\n== [{qlabel}] {q}")
            for r in out:
                if r["svc"] == svc and r["q"] == qlabel:
                    err = f"  !! ERROR: {r['error']}" if r["error"] else ""
                    print(f"  -- mode={r['mode']}  {r['secs']}s  usage={json.dumps(r['usage'])}{err}")
                    for i, res in enumerate(r["results"][:5], 1):
                        if "s" in res:
                            extra = f" score={res['s']:.2f}" if isinstance(res.get("s"), (int, float)) else ""
                        else:
                            extra = f" {res.get('d') or 'no-date'}"
                        print(f"     {i}. {res['t'][:66]}{extra}")
    print("\nsaved -> search_results/mode_quality.json")
