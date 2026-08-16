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
| `extract_test.py` | Anti-block fetch matrix on 5 community sites | ~free + 2 credits |
| `mode_quality_test.py` | Result quality across search modes/depths | ~$0.10 + 24 credits |
| `feature_test.py` | 14 special-feature checks (params, gotchas) | ~$0.05 + 6 credits |
| `batch_compare.py` | 20 categorized queries + link checks + cost | ~$0.14 + 20 credits |
| `smoke_test.py` | **Drift check**: load-bearing facts still true | ~$0.03 + 4 credits |
| `validate_repo.py` | Repo hygiene: frontmatter, leaks, references | free |

## Updating the evidence

1. Run the relevant script(s): `python tests/batch_compare.py`
2. Compare fresh output against the numbers in `references/evidence.md`
3. Update `evidence.md` (numbers + "as of" dates), never overwrite history —
   note what changed
4. Bump the version per `MAINTENANCE.md` and add a CHANGELOG entry

See `MAINTENANCE.md` for cadence and versioning rules.
