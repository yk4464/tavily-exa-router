"""Latency benchmark: Tavily vs Exa.

Round A: head-to-head, default-ish params, 5 interleaved runs each.
Round B: per-service mode/depth sweep, 2 runs each.
Round C: with content extraction enabled, 3 runs each.
"""
import json
import os
import statistics
import time
import urllib.request

TAVILY_KEY = os.environ["TAVILY_API_KEY"]
EXA_KEY = os.environ["EXA_API_KEY"]


def post(url, payload, headers, timeout=90):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def tavily(payload):
    post("https://api.tavily.com/search", payload,
         {"Authorization": f"Bearer {TAVILY_KEY}"})


def exa(payload):
    post("https://api.exa.ai/search", payload, {"x-api-key": EXA_KEY})


def bench(label, fn, payload, runs=3):
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        try:
            fn(payload)
            times.append(time.perf_counter() - t0)
        except Exception as exc:  # noqa: BLE001
            print(f"  {label}: ERROR {exc}")
            return
    ms = [t * 1000 for t in times]
    print(f"  {label:<38} min={min(ms):6.0f}  med={statistics.median(ms):6.0f}  "
          f"avg={statistics.mean(ms):6.0f}  max={max(ms):6.0f} ms  (n={runs})")
    return statistics.median(ms)


Q = "artificial intelligence industry trends"

print("=" * 78)
print("Round A: head-to-head, default params, 5 results, interleaved (5 runs)")
print("=" * 78)
t_pl = {"query": Q, "max_results": 5, "search_depth": "basic"}
e_pl = {"query": Q, "numResults": 5, "type": "auto"}
# interleave manually: bench helper runs sequentially, so emulate via 1-run passes
t_times, e_times = [], []
for i in range(5):
    for name, fn, pl, acc in (("tavily", tavily, t_pl, t_times), ("exa", exa, e_pl, e_times)):
        t0 = time.perf_counter()
        fn(pl)
        acc.append((time.perf_counter() - t0) * 1000)
for name, acc in (("Tavily basic", t_times), ("Exa auto", e_times)):
    print(f"  {name:<38} min={min(acc):6.0f}  med={statistics.median(acc):6.0f}  "
          f"avg={statistics.mean(acc):6.0f}  max={max(acc):6.0f} ms  (n=5)")

print()
print("=" * 78)
print("Round B: mode/depth sweep (2 runs each)")
print("=" * 78)
for depth in ("ultra-fast", "fast", "basic", "advanced"):
    bench(f"Tavily search_depth={depth}", tavily,
          {"query": Q, "max_results": 5, "search_depth": depth}, runs=2)
for mode in ("instant", "fast", "auto", "deep-lite"):
    bench(f"Exa type={mode}", exa,
          {"query": Q, "numResults": 5, "type": mode}, runs=2)

print()
print("=" * 78)
print("Round C: with content extraction, 3 results (3 runs)")
print("=" * 78)
bench("Tavily include_raw_content=markdown", tavily,
      {"query": Q, "max_results": 3, "search_depth": "basic",
       "include_raw_content": "markdown"}, runs=3)
bench("Exa contents.text maxCharacters=500", exa,
      {"query": Q, "numResults": 3, "type": "auto",
       "contents": {"text": {"maxCharacters": 500}}}, runs=3)
bench("Exa contents.text + highlights", exa,
      {"query": Q, "numResults": 3, "type": "auto",
       "contents": {"text": {"maxCharacters": 500},
                    "highlights": {"maxCharacters": 300}}}, runs=3)
