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
| `feature_test.py` | 14 special-feature checks (params, gotchas) | ~$0.05 + 6 credits |
| `batch_compare.py` | 20 categorized queries + link checks + cost | ~$0.14 + 20 credits |
| `smoke_test.py` | **Drift check**: load-bearing facts still true | ~$0.03 + 4 credits |
| `validate_repo.py` | Repo hygiene: frontmatter, leaks, references | free |
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
4. Bump the version per `MAINTENANCE.md` and add a CHANGELOG entry

See `MAINTENANCE.md` for cadence and versioning rules.
