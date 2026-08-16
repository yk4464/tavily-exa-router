"""Phase 3b: special-feature validation for Tavily and Exa.

Each feature gets 1-2 calls; outcome printed compactly and saved to JSON.
"""
import json
import os
import time
import urllib.request

TAVILY_KEY = os.environ["TAVILY_API_KEY"]
EXA_KEY = os.environ["EXA_API_KEY"]


def post(url, payload, headers, timeout=240):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def tavily(payload):
    return post("https://api.tavily.com/search", payload,
                {"Authorization": f"Bearer {TAVILY_KEY}"})


def exa(payload):
    return post("https://api.exa.ai/search", payload, {"x-api-key": EXA_KEY})


out = []


def record(name, svc, payload, summary):
    t0 = time.perf_counter()
    try:
        fn = tavily if svc == "tavily" else exa
        data = fn(payload)
        out.append({"name": name, "svc": svc, "payload": payload,
                    "secs": round(time.perf_counter() - t0, 1), "data": data})
        print(summary(data))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:200]
        out.append({"name": name, "svc": svc, "payload": payload, "error": f"HTTP {e.code}: {body}"})
        print(f"  [{name}] HTTP {e.code}: {body}")
    except Exception as e:  # noqa: BLE001
        out.append({"name": name, "svc": svc, "payload": payload, "error": str(e)})
        print(f"  [{name}] ERROR {e}")


def rlist(data, n=3, dated=False):
    rs = data.get("results", [])[:n]
    return " | ".join(f"{(r.get('title') or '')[:38]}"
                      + (f" ({(r.get('publishedDate') or '')[:10]})" if dated else "")
                      for r in rs)


print("== TAVILY features ==")
record("tavily:include_answer(basic)", "tavily",
       {"query": "what is retrieval augmented generation", "include_answer": "basic", "max_results": 3},
       lambda d: f"  answer: {(d.get('answer') or '')[:180]}")
record("tavily:include_answer(advanced)", "tavily",
       {"query": "what is retrieval augmented generation", "include_answer": "advanced", "max_results": 3},
       lambda d: f"  answer: {(d.get('answer') or '')[:280]}")
record("tavily:news+time_range", "tavily",
       {"query": "AI regulation policy", "topic": "news", "time_range": "week", "max_results": 5},
       lambda d: f"  {len(d.get('results', []))} results: {rlist(d, 3)}")
record("tavily:exact_match", "tavily",
       {"query": '"retrieval augmented generation" survey', "exact_match": True, "max_results": 5},
       lambda d: f"  {len(d.get('results', []))} results: {rlist(d, 3)}")
record("tavily:include_domains(arxiv)", "tavily",
       {"query": "transformer attention mechanism", "include_domains": ["arxiv.org"], "max_results": 5},
       lambda d: f"  {len(d.get('results', []))} results, all arxiv? "
                 f"{all('arxiv' in r.get('url', '') for r in d.get('results', []))}: {rlist(d, 3)}")
record("tavily:country(germany)", "tavily",
       {"query": "best electric cars 2026", "country": "germany", "max_results": 5},
       lambda d: f"  domains: {', '.join(__import__('urllib.parse', fromlist=['urlparse']).urlparse(r.get('url','')).netloc for r in d.get('results', [])[:5])}")

print("\n== EXA features ==")
record("exa:outputSchema", "exa",
       {"query": "best vector databases 2026", "numResults": 10, "type": "auto",
        "outputSchema": {"type": "object", "properties": {
            "databases": {"type": "array", "items": {"type": "object", "properties": {
                "name": {"type": "string"}, "url": {"type": "string"},
                "best_for": {"type": "string"}}}}}}},
       lambda d: f"  structured output: {json.dumps(d.get('output'))[:400]}")
record("exa:highlights", "exa",
       {"query": "sqlite vs postgres production", "numResults": 3, "type": "auto",
        "contents": {"highlights": {"query": "concurrency write performance", "maxCharacters": 200}}},
       lambda d: "  " + " || ".join((r.get("highlights") or ["?"])[0][:90] for r in d.get("results", [])))
record("exa:summary", "exa",
       {"query": "mcp model context protocol adoption", "numResults": 3, "type": "auto",
        "contents": {"summary": {"query": "main adoption blockers"}}},
       lambda d: "  " + " || ".join((r.get("summary") or "?")[:110] for r in d.get("results", [])))
record("exa:subpages", "exa",
       {"query": "Tavily AI search API", "numResults": 2, "type": "auto",
        "contents": {"subpages": 2, "subpageTarget": "pricing"}},
       lambda d: f"  {json.dumps([{'main': r.get('url'), 'subs': [s.get('url') for s in (r.get('subpages') or [])][:3]} for r in d.get('results', [])])[:350]}")
record("exa:startPublishedDate(7d)", "exa",
       {"query": "AI model releases", "numResults": 5, "type": "auto",
        "startPublishedDate": "2026-08-10T00:00:00Z"},
       lambda d: f"  {len(d.get('results', []))} results: {rlist(d, 4, dated=True)}")
record("exa:category=company", "exa",
       {"query": "Exa AI search", "numResults": 5, "category": "company"},
       lambda d: f"  {json.dumps([r.get('title') for r in d.get('results', [])[:5]])[:250]}")
record("exa:company+date(expect-400)", "exa",
       {"query": "Exa AI search", "numResults": 5, "category": "company",
        "startPublishedDate": "2026-01-01T00:00:00Z"},
       lambda d: f"  unexpectedly OK: {rlist(d, 2)}")
record("exa:includeDomains(wildcard)", "exa",
       {"query": "machine learning engineering", "numResults": 5, "type": "auto",
        "includeDomains": ["*.substack.com"]},
       lambda d: f"  {len(d.get('results', []))} results, all substack? "
                 f"{all('substack' in r.get('url', '') for r in d.get('results', []))}")

os.makedirs("search_results", exist_ok=True)
with open("search_results/features.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("\nsaved -> search_results/features.json")
