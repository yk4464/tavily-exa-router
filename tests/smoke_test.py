"""Cheap drift check (~$0.03): verifies the skill's load-bearing facts still hold.

Run from anywhere with TAVILY_API_KEY and EXA_API_KEY set:
    python tests/smoke_test.py

Exits 0 if secrets are absent (so CI stays green until configured) and
nonzero when a documented fact has drifted, so CI can flag it.
"""
import json
import os
import sys
import urllib.request

TAVILY_KEY = os.environ.get("TAVILY_API_KEY")
EXA_KEY = os.environ.get("EXA_API_KEY")

if not TAVILY_KEY or not EXA_KEY:
    print("SKIP: set TAVILY_API_KEY and EXA_API_KEY to enable drift checks.")
    sys.exit(0)


def post(url, payload, headers):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers}, method="POST")
    return urllib.request.urlopen(req, timeout=120)


results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(f"  {'PASS' if ok else 'DRIFT'}  {name}" + (f" — {detail}" if detail else ""))


# 1. Tavily basic search still works and bills 1 credit
try:
    with post("https://api.tavily.com/search",
              {"query": "python requests library", "max_results": 3,
               "search_depth": "basic", "include_usage": True},
              {"Authorization": f"Bearer {TAVILY_KEY}"}) as r:
        d = json.load(r)
    credits = (d.get("usage") or {}).get("credits")
    check("Tavily basic search works", bool(d.get("results")))
    check("Tavily basic still bills 1 credit", credits == 1, f"credits={credits}")
except Exception as e:  # noqa: BLE001
    check("Tavily basic search works", False, str(e))

# 2. Tavily /extract still fetches a benign public page
try:
    with post("https://api.tavily.com/extract",
              {"urls": ["https://example.com"]},
              {"Authorization": f"Bearer {TAVILY_KEY}"}) as r:
        d = json.load(r)
    ok = bool(d.get("results")) and len(d["results"][0].get("raw_content") or "") > 50
    check("Tavily /extract fetches a public page", ok)
except Exception as e:  # noqa: BLE001
    check("Tavily /extract fetches a public page", False, str(e))

# 3. Exa auto search still works and prices at the documented level
try:
    with post("https://api.exa.ai/search",
              {"query": "python requests library", "numResults": 3, "type": "auto"},
              {"x-api-key": EXA_KEY}) as r:
        d = json.load(r)
    cost = d.get("costDollars")
    total = cost.get("total") if isinstance(cost, dict) else cost
    check("Exa auto search works", bool(d.get("results")))
    check("Exa auto price sane (<= $0.02)", total is not None and total <= 0.02,
          f"${total}")
except Exception as e:  # noqa: BLE001
    check("Exa auto search works", False, str(e))

# 4. Documented pitfall still holds: company + startPublishedDate => HTTP 400
try:
    post("https://api.exa.ai/search",
         {"query": "example", "numResults": 2, "category": "company",
          "startPublishedDate": "2026-01-01T00:00:00Z"},
         {"x-api-key": EXA_KEY})
    check("Exa company+date still rejected (400)", False, "accepted — pitfall fixed upstream?")
except urllib.error.HTTPError as e:
    check("Exa company+date still rejected (400)", e.code == 400, f"HTTP {e.code}")
except Exception as e:  # noqa: BLE001
    check("Exa company+date still rejected (400)", False, str(e))

print(f"\n{sum(results)}/{len(results)} checks passed.")
sys.exit(0 if all(results) else 1)
