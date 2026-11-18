"""Cheap drift check (~$0.062): verifies the skill's load-bearing facts still hold.

Run from anywhere with TAVILY_API_KEY and EXA_API_KEY set:
    python tests/smoke_test.py

Exits 0 if secrets are absent (so CI stays green until configured) and
nonzero when a documented fact has drifted, so CI can flag it.

Exit codes keep the two kinds of red run apart:
    0  every check passed (or the secrets were absent)
    1  a documented fact drifted — re-test it and update the docs
    2  infrastructure failed only (network, rate limit, 5xx, auth, quota) —
       re-run; the run says nothing about drift
"""
import datetime
import email.utils
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.request

# Documented Exa prices per request with up to 10 results, from SKILL.md
# "Mode selection"; Tavily bills credits per search_depth. Prices are the
# fastest-rotting facts in this repo, so each one is pinned to the exact
# documented value instead of bounded by an upper limit.
EXA_LITE = 0.004  # recommended replacement for `instant`; same price
EXA_INSTANT = 0.004
EXA_AUTO = 0.007  # `fast` bills the same
EXA_DEEP = 0.012  # `deep-lite` bills the same
EXA_DEEP_REASONING = 0.015
EXA_PER_RESULT = 0.001  # each returned result beyond 10
PRICE_TOL = 1e-6

RETRY_STATUSES = {408, 429, 434, 500, 502, 503, 504}
AUTH_OR_QUOTA_STATUSES = {401, 402, 403, 432, 433}
MAX_ATTEMPTS = 3

QUERY = "python requests library"
EXA_SEARCH = "https://api.exa.ai/search"


class ProviderError(Exception):
    """No provider answer was produced: network trouble, rate limiting,
    auth, or a body that was not JSON. Says nothing about drift."""


def _retry_after(exc, fallback):
    """Retry-After is delta-seconds or an HTTP-date (RFC 7231); a legal
    header must never tear the run down, so both parses are guarded."""
    headers = getattr(exc, "headers", None)
    header = headers.get("Retry-After") if headers is not None else None
    if not header:
        return fallback
    try:
        seconds = float(header)
    except ValueError:
        try:
            when = email.utils.parsedate_to_datetime(header)
        except (TypeError, ValueError):
            return fallback
        if when is None:
            return fallback
        if when.tzinfo is None:
            when = when.replace(tzinfo=datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        seconds = (when - now).total_seconds()
    if seconds != seconds or seconds < 0:  # NaN, or a date already past
        return fallback
    return min(seconds, 10.0)


def post(url, payload, headers):
    """POST JSON, retrying rate limits, 5xx, and transport failures.

    A 429 or a dropped connection is noise from the provider's side; letting
    it reach a check would report drift and send maintainers to edit docs
    that are still correct.
    """
    for attempt in range(MAX_ATTEMPTS):
        last = attempt + 1 == MAX_ATTEMPTS
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", **headers},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code in RETRY_STATUSES:
                if not last:
                    time.sleep(_retry_after(exc, 2.0 * (attempt + 1)))
                    continue
                raise ProviderError(
                    f"HTTP {exc.code} after {MAX_ATTEMPTS} attempts") from exc
            if exc.code in AUTH_OR_QUOTA_STATUSES:
                raise ProviderError(
                    f"HTTP {exc.code} — check the API key, plan, or quota") from exc
            raise
        except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
            if not last:
                time.sleep(2.0 * (attempt + 1))
                continue
            reason = getattr(exc, "reason", exc)
            raise ProviderError(f"{type(exc).__name__}: {reason}") from exc
        except ValueError as exc:
            # A 200 whose body is not JSON is a gateway page, not an answer.
            if not last:
                time.sleep(2.0 * (attempt + 1))
                continue
            raise ProviderError(f"response body was not JSON: {exc}") from exc
    raise ProviderError("retry loop exhausted")


PASS, DRIFT, ERROR, SKIP = "PASS", "DRIFT", "ERROR", "SKIP"
results = []
fetched = {}


def record(name, status, detail=""):
    results.append((name, status))
    print(f"  {status:<7} {name}" + (f" — {detail}" if detail else ""))
    if status == SKIP:
        print(f"::warning::{name} — {detail}")


def fetch(name, url, payload, headers):
    """One provider call per name; checks read the cached entry."""
    try:
        entry = {"data": post(url, payload, headers), "error": None,
                 "code": None, "infra": False}
    except urllib.error.HTTPError as exc:
        # A 4xx answer is a provider verdict on our request: that is drift
        # when a check expected the request to succeed. Keep the body: some
        # documented rejections must name the offending field.
        entry = {"data": None, "error": f"HTTP {exc.code}", "code": exc.code,
                 "body": exc.read().decode("utf-8", "ignore")[:800],
                 "infra": False}
    except ProviderError as exc:
        entry = {"data": None, "error": str(exc), "code": None, "body": None,
                 "infra": True}
    except Exception as exc:  # noqa: BLE001
        entry = {"data": None, "error": f"{type(exc).__name__}: {exc}",
                 "code": None, "body": None, "infra": True}
    fetched[name] = entry


def check(name, source, evaluate):
    """Register exactly one result per check, whatever the network did.

    `evaluate` returns (verdict, detail); a None verdict means the response
    could not exercise the fact (reported, never counted as drift).
    """
    entry = fetched[source]
    if entry["error"]:
        record(name, ERROR if entry["infra"] else DRIFT, entry["error"])
        return
    try:
        verdict, detail = evaluate(entry["data"])
    except Exception as exc:  # noqa: BLE001
        record(name, DRIFT, f"{type(exc).__name__}: {exc}")
        return
    if verdict is None:
        record(name, SKIP, detail)
    else:
        record(name, PASS if verdict else DRIFT, detail)


def check_rejected(name, source, expected_code, field=None):
    """A documented pitfall is an expected 4xx: status is the fact.

    With `field`, the documented contract also requires the body to name the
    unsupported parameter; a 400 that names nothing is not the same fact.
    """
    entry = fetched[source]
    if entry["code"] == expected_code:
        if field is None:
            record(name, PASS, f"HTTP {expected_code}")
            return
        body = entry["body"] or ""
        if field in body:
            record(name, PASS, f"HTTP {expected_code}, body names {field}")
        else:
            record(name, DRIFT,
                   f"HTTP {expected_code} but body does not name {field}: {body[:180]}")
    elif entry["code"] is not None:
        record(name, DRIFT, f"HTTP {entry['code']} (expected {expected_code})")
    elif entry["infra"]:
        record(name, ERROR, entry["error"])
    else:
        record(name, DRIFT, "accepted — pitfall fixed upstream?")


def cost_total(data):
    """Exa bills through `costDollars`; the object form carries `total`."""
    cost = data.get("costDollars")
    if isinstance(cost, dict):
        cost = cost.get("total")
    if isinstance(cost, bool) or not isinstance(cost, (int, float)):
        raise ValueError(f"costDollars total is {type(cost).__name__}({cost!r})")
    return float(cost)


def credits(data):
    usage = data.get("usage")
    value = usage.get("credits") if isinstance(usage, dict) else usage
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"usage.credits is {type(value).__name__}({value!r})")
    return value


def price(expected):
    def evaluate(data):
        total = cost_total(data)
        return (abs(total - expected) < PRICE_TOL,
                f"USD {total:g} (documented: {expected:g})")
    return evaluate


def linear_price(data):
    total = cost_total(data)
    returned = len(data.get("results") or [])
    if returned <= 10:
        return None, f"only {returned} results returned — tier not exercised"
    expected = EXA_AUTO + (returned - 10) * EXA_PER_RESULT
    return (abs(total - expected) < PRICE_TOL,
            f"{returned} results, USD {total:g} (documented: {expected:g})")


def credit_bill(expected):
    def evaluate(data):
        value = credits(data)
        return value == expected, f"credits={value}"
    return evaluate


def tavily_basic_works(data):
    found = data.get("results") or []
    return bool(found), f"{len(found)} results"


def tavily_extract_works(data):
    items = data.get("results") or []
    size = len(items[0].get("raw_content") or "") if items else 0
    return (bool(items) and size > 50,
            f"{len(items)} url(s), raw_content {size} chars")


def exa_auto_works(data):
    found = data.get("results") or []
    return bool(found), f"{len(found)} results"


def main():
    tavily_key = os.environ.get("TAVILY_API_KEY")
    exa_key = os.environ.get("EXA_API_KEY")
    if not tavily_key or not exa_key:
        missing = [name for name, value in (("TAVILY_API_KEY", tavily_key),
                                            ("EXA_API_KEY", exa_key)) if not value]
        print("SKIP: set TAVILY_API_KEY and EXA_API_KEY to enable drift checks.")
        print(f"::warning::drift check skipped — missing {', '.join(missing)}")
        return 0

    results.clear()
    fetched.clear()
    exa_headers = {"x-api-key": exa_key}
    tavily_headers = {"Authorization": f"Bearer {tavily_key}"}

    # Tavily: search_depth is the only documented cost lever (1 vs 2 credits),
    # and /extract bills 1 credit for a single URL.
    fetch("tavily basic", "https://api.tavily.com/search",
          {"query": QUERY, "max_results": 3, "search_depth": "basic",
           "include_usage": True}, tavily_headers)
    fetch("tavily extract", "https://api.tavily.com/extract",
          {"urls": ["https://example.com"]}, tavily_headers)
    fetch("tavily advanced", "https://api.tavily.com/search",
          {"query": QUERY, "max_results": 3, "search_depth": "advanced",
           "include_usage": True}, tavily_headers)

    check("Tavily basic search returns results", "tavily basic",
          tavily_basic_works)
    check("Tavily basic bills 1 credit", "tavily basic", credit_bill(1))
    check("Tavily /extract fetches a public page", "tavily extract",
          tavily_extract_works)
    check("Tavily advanced bills 2 credits", "tavily advanced", credit_bill(2))

    # Exa: one call per documented price tier, all inside the up-to-10-result
    # band where the per-request price is flat.
    fetch("exa auto", EXA_SEARCH,
          {"query": QUERY, "numResults": 10, "type": "auto"}, exa_headers)
    fetch("exa instant", EXA_SEARCH,
          {"query": QUERY, "numResults": 3, "type": "instant"}, exa_headers)
    fetch("exa lite", EXA_SEARCH,
          {"query": QUERY, "numResults": 3, "type": "lite"}, exa_headers)
    fetch("exa deep", EXA_SEARCH,
          {"query": QUERY, "numResults": 3, "type": "deep"}, exa_headers)
    fetch("exa deep-lite", EXA_SEARCH,
          {"query": QUERY, "numResults": 3, "type": "deep-lite"}, exa_headers)
    fetch("exa deep-reasoning", EXA_SEARCH,
          {"query": QUERY, "numResults": 3, "type": "deep-reasoning"}, exa_headers)
    # 11 results is the smallest request that crosses the free band; billing
    # follows what comes back, so a thin index makes this check inconclusive.
    fetch("exa eleven", EXA_SEARCH,
          {"query": QUERY, "numResults": 11, "type": "auto"}, exa_headers)

    check("Exa auto search returns results", "exa auto", exa_auto_works)
    check("Exa auto (up to 10 results) costs USD 0.007", "exa auto",
          price(EXA_AUTO))
    check("Exa instant (up to 10 results) costs USD 0.004", "exa instant",
          price(EXA_INSTANT))
    check("Exa lite (up to 10 results) costs USD 0.004", "exa lite",
          price(EXA_LITE))
    check("Exa deep (up to 10 results) costs USD 0.012", "exa deep",
          price(EXA_DEEP))
    check("Exa deep-lite (up to 10 results) costs USD 0.012", "exa deep-lite",
          price(EXA_DEEP))
    check("Exa deep-reasoning (up to 10 results) costs USD 0.015",
          "exa deep-reasoning", price(EXA_DEEP_REASONING))
    check("Exa results beyond 10 add USD 0.001 each", "exa eleven",
          linear_price)

    # Documented pitfall: company category + startPublishedDate => HTTP 400.
    fetch("exa company+date", EXA_SEARCH,
          {"query": "example", "numResults": 2, "category": "company",
           "startPublishedDate": "2026-01-01T00:00:00Z"}, exa_headers)
    check_rejected("Exa company+date still rejected (400)", "exa company+date",
                   400)

    # Documented pitfall: `lite` accepts a restricted parameter set and rejects
    # `outputSchema` with a 400 that names the field.
    fetch("exa lite+outputSchema", EXA_SEARCH,
          {"query": QUERY, "numResults": 3, "type": "lite",
           "outputSchema": {"type": "object",
                            "properties": {"answer": {"type": "string"}}}},
          exa_headers)
    check_rejected("Exa lite rejects outputSchema (400, field named)",
                   "exa lite+outputSchema", 400, field="outputSchema")

    tally = {status: sum(1 for _, s in results if s == status)
             for status in (PASS, DRIFT, ERROR, SKIP)}
    print(f"\n{tally[PASS]}/{len(results)} checks passed"
          f" (drift {tally[DRIFT]}, infrastructure {tally[ERROR]},"
          f" inconclusive {tally[SKIP]}).")
    if tally[DRIFT]:
        print("Re-test the drifted facts, then update SKILL.md and references.")
        return 1
    if tally[ERROR]:
        print("Only infrastructure failed; re-run before touching the docs.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
