# Tests — the evidence regeneration kit

All scripts are Python 3 stdlib-only (no pip installs). They read
`TAVILY_API_KEY` and `EXA_API_KEY` from the environment and write raw
output into `search_results/` (git-ignored — the curated summary lives in
`references/evidence.md`).

| Script | What it measures | Approx. cost per full run |
|---|---|---|
| `search_compare.py` | Same query on both services, side by side | ~$0.01 + 2 credits |
| `speed_test.py` | Latency: defaults, mode sweep, content extraction | ~$0.05 + ~30 credits |
| `community_test.py` | Community/forum content coverage (EN+CN) | ~$0.02 + 2 credits |
| `extract_test.py` | Legacy focused fetch matrix on 5 community sites | ~free + 2 credits |
| `mode_quality_test.py` | Result quality across search modes/depths | ~$0.10 + 24 credits |
| `lite_quality_test.py` | Exa `lite` vs `instant`/`fast`/`auto` on news, academic, and Chinese queries: counts, dates, allowlist hits, latency, cost, contents-drop ratio, `startPublishedDate` windows, `lite` 400s, and Tavily `include_published_date` coverage. Writes `search_results/lite_quality.json`; blind quality scoring runs outside the script | ~$1.68 + 9 credits |
| `feature_test.py` | 14 special-feature checks (params, gotchas) | ~$0.05 + 6 credits |
| `batch_compare.py` | 20 categorized queries + link checks + cost | ~$0.14 + 20 credits |
| `smoke_test.py` | **Drift check**: 14 load-bearing facts (Tavily basic/advanced credits, Exa per-type prices including `lite`, the per-result surcharge above 10, `company` + date rejected, `lite` + `outputSchema` rejected with the field named). Exit 0 = pass or skipped (no keys; emits a `::warning::`), 1 = drift, 2 = infrastructure-only failure (network, rate limit, 401/403) — re-run before editing docs | ~$0.062 + 4 credits |
| `validate_repo.py` | Repo hygiene: frontmatter, leaks, version alignment, evals, reference and `§` anchor integrity, and a rule-only `SKILL.md` (no dates, `references/…` paths or `§` anchors) | free |
| `comprehensive_benchmark.py` | Search/Extract/Contents modes, parameters, boundaries, paired semantic checks, SSE parsing, and a 13-site fetch matrix | variable; prints recorded usage/cost |

The comprehensive benchmark intentionally avoids a meaningless Cartesian
product. It tests every in-scope parameter independently, every documented
mode, important conflicts and boundaries, four quality query types, and 13
known-URL targets. Several cases use same-query controls so a 200 response is
not mistaken for proof that a parameter had an effect. Run all suites or one
section:

```bash
python tests/comprehensive_benchmark.py --suite all
python tests/comprehensive_benchmark.py --suite modes
python tests/comprehensive_benchmark.py --suite parameters
python tests/comprehensive_benchmark.py --suite extract
```

Raw responses and summaries are saved under `search_results/`. API keys are
read only from the process environment and are never written to output.

Review notes:

- Search-mode counts use domain allowlists and near-duplicate URL heuristics;
  manually inspect every fixed query before changing a routing rule.
- A successful fetch may contain a login wall, wrong page, short shell, or
  prompt-injection text. Check classification and per-URL failure fields.
- Preserve documented limits when the live endpoint happens to accept an
  out-of-range value; record that behavior as drift, not as a supported feature.

## Updating the evidence

1. Run the relevant script(s): `python tests/batch_compare.py`
2. Compare fresh output against the numbers in `references/evidence.md`
3. Update `evidence.md` (numbers + "as of" dates), never overwrite history —
   note what changed
4. Keep `SKILL.md` out of it: it states the rule, never the run, the date or
   the source. `python tests/validate_repo.py` fails if a date, a
   `references/…` path or a `§` anchor shows up there
5. Bump the version per `MAINTENANCE.md` and add a CHANGELOG entry saying
   why the rule changed

## Evaluation suites (`evals/`)

`evals/evals.json` contains 26 routing/scope/failure-handling evaluation cases
used to verify that an agent picks the right provider, mode, and parameters
for a given query profile, and handles failures, costs, dedupe, and untrusted
content as `SKILL.md` specifies. There is no runner in this repository: run
them manually through a skill-eval harness. CI only validates their structure.

`evals/trigger-set.json` is the fixed trigger set (10 should-trigger, 10
confusable should-not-trigger) behind the 1.5.0 `description`. Each trial is an
isolated model call whose system prompt lists every installed skill's name and
description plus the host's built-in and Tavily/Exa tools, and asks which
skills it would load; a trial counts as triggered when the reply names
`tavily-exa-router`. Use at least 3 (odd) trials per case and the same set for
the baseline and the candidate. Score with the `oil-skill-creator` skill's
`scripts/score_triggers.py`:

```bash
python score_triggers.py evals/trigger-set.json <baseline-results.json> --skill-path <baseline-skill> --phase select --strict --output trigger-baseline-select.json
python score_triggers.py evals/trigger-set.json <candidate-results.json> --skill-path <candidate-skill> --phase select --strict --baseline-report trigger-baseline-select.json --output trigger-candidate-select.json
```

2026-10-31 result (5 trials per case, single model): holdout accuracy 0.875 →
1.00, no regressions; the only difference was "Use Exa for this" being read as
a skip by the 1.4.0 description.

See `MAINTENANCE.md` for cadence and versioning rules.
