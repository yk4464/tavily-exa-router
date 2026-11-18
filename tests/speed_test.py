"""Latency benchmark: Tavily vs Exa.

Round A: head-to-head, default-ish params, 5 interleaved runs each.
Round B: per-service mode/depth sweep, 2 runs each.
Round C: with content extraction enabled, 3 runs each.

A failed call is recorded and skipped: the remaining samples and rounds still
run, and every collected timing is written to search_results/speed_test.json.
"""
import argparse
import json
import os
import statistics
import time
import urllib.request
from pathlib import Path


def api_key(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"missing environment variable {name}; set it before running this script")
    return value


TAVILY_KEY = None
EXA_KEY = None

OUT_DIR = Path(__file__).resolve().parent.parent / "search_results"


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


def report(label, ms, errors):
    """Print and return one sample set; empty sample sets stay in the JSON."""
    entry = {"samples_ms": [round(t, 1) for t in ms], "errors": errors}
    if ms:
        entry.update({
            "n": len(ms),
            "min_ms": round(min(ms)),
            "median_ms": round(statistics.median(ms)),
            "mean_ms": round(statistics.mean(ms)),
            "max_ms": round(max(ms)),
        })
        print(f"  {label:<38} min={entry['min_ms']:6.0f}  med={entry['median_ms']:6.0f}  "
              f"avg={entry['mean_ms']:6.0f}  max={entry['max_ms']:6.0f} ms  (n={len(ms)})")
    else:
        print(f"  {label:<38} no successful samples")
    return entry


def bench(label, fn, payload, runs=3):
    times, errors = [], []
    for _ in range(runs):
        t0 = time.perf_counter()
        try:
            fn(payload)
        except Exception as exc:  # noqa: BLE001 - one failed sample must not end the run
            errors.append(str(exc))
            print(f"  {label}: ERROR {exc}")
            continue
        times.append((time.perf_counter() - t0) * 1000)
    return report(label, times, errors)


def main():
    global TAVILY_KEY, EXA_KEY, OUT_DIR
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR, help="directory for raw JSON output")
    args = parser.parse_args()

    TAVILY_KEY = api_key("TAVILY_API_KEY")
    EXA_KEY = api_key("EXA_API_KEY")
    OUT_DIR = args.out_dir

    results = {"round_a": {}, "round_b": {}, "round_c": {}, "partial": True}
    Q = "artificial intelligence industry trends"

    # Fail on an unwritable output directory before spending any API calls.
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUT_DIR / "speed_test.json"

    try:
        print("=" * 78)
        print("Round A: head-to-head, default params, 5 results, interleaved (5 runs)")
        print("=" * 78)
        t_pl = {"query": Q, "max_results": 5, "search_depth": "basic"}
        e_lite_pl = {"query": Q, "numResults": 5, "type": "lite"}
        e_inst_pl = {"query": Q, "numResults": 5, "type": "instant"}
        e_auto_pl = {"query": Q, "numResults": 5, "type": "auto"}
        # interleave manually: bench helper runs sequentially, so emulate via 1-run passes
        t_times, e_lite_t, e_inst_t, e_auto_t = [], [], [], []
        t_err, e_lite_err, e_inst_err, e_auto_err = [], [], [], []
        for i in range(5):
            for name, fn, pl, acc, errors in (
                    ("tavily_basic", tavily, t_pl, t_times, t_err),
                    ("exa_lite", exa, e_lite_pl, e_lite_t, e_lite_err),
                    ("exa_instant", exa, e_inst_pl, e_inst_t, e_inst_err),
                    ("exa_auto", exa, e_auto_pl, e_auto_t, e_auto_err)):
                t0 = time.perf_counter()
                try:
                    fn(pl)
                except Exception as exc:  # noqa: BLE001 - keep the samples already taken
                    errors.append({"run": i + 1, "error": str(exc)})
                    print(f"  {name} run {i + 1}: ERROR {exc}")
                    continue
                acc.append((time.perf_counter() - t0) * 1000)
        results["round_a"]["tavily_basic"] = report("Tavily basic", t_times, t_err)
        results["round_a"]["exa_lite"] = report("Exa lite", e_lite_t, e_lite_err)
        results["round_a"]["exa_instant"] = report("Exa instant", e_inst_t, e_inst_err)
        results["round_a"]["exa_auto"] = report("Exa auto", e_auto_t, e_auto_err)

        print()
        print("=" * 78)
        print("Round B: mode/depth sweep (2 runs each)")
        print("=" * 78)
        for depth in ("ultra-fast", "fast", "basic", "advanced"):
            results["round_b"][f"tavily:{depth}"] = bench(
                f"Tavily search_depth={depth}", tavily,
                {"query": Q, "max_results": 5, "search_depth": depth}, runs=2)
        for mode in ("lite", "instant", "fast", "auto", "deep-lite", "deep"):
            results["round_b"][f"exa:{mode}"] = bench(
                f"Exa type={mode}", exa,
                {"query": Q, "numResults": 5, "type": mode}, runs=2)

        print()
        print("=" * 78)
        print("Round C: with content extraction, 3 results (3 runs)")
        print("=" * 78)
        results["round_c"]["tavily:raw_markdown"] = bench(
            "Tavily include_raw_content=markdown", tavily,
            {"query": Q, "max_results": 3, "search_depth": "basic",
             "include_raw_content": "markdown"}, runs=3)
        results["round_c"]["exa:lite_text_500"] = bench(
            "Exa lite contents.text maxCharacters=500", exa,
            {"query": Q, "numResults": 3, "type": "lite",
             "contents": {"text": {"maxCharacters": 500}}}, runs=3)
        results["round_c"]["exa:text_500"] = bench(
            "Exa auto contents.text maxCharacters=500", exa,
            {"query": Q, "numResults": 3, "type": "auto",
             "contents": {"text": {"maxCharacters": 500}}}, runs=3)
        results["round_c"]["exa:text_highlights"] = bench(
            "Exa auto contents.text + highlights", exa,
            {"query": Q, "numResults": 3, "type": "auto",
             "contents": {"text": {"maxCharacters": 500},
                          "highlights": {"maxCharacters": 300}}}, runs=3)
        results["partial"] = False
    finally:
        output.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nsaved -> {output}")


if __name__ == "__main__":
    main()
