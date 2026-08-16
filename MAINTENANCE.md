# Maintenance

This repo's value is dated, reproducible evidence — which decays. This file
is the playbook for keeping it honest.

## What rots, fastest first

1. **Prices, quotas, free tiers** — Exa already raised $5→$7/1k once
2. **Anti-block matrix** (which sites `/extract` vs `/contents` can fetch) —
   changes month to month
3. **Parameter names, modes, deprecations** — renamed or removed over time
4. **Quality/overlap conclusions** — index composition drifts slowly

## Cadence

| When | What |
|---|---|
| Monthly (automated) | `tests/smoke_test.py` via GitHub Actions — flags drift in load-bearing facts (costs ~$0.03) |
| Quarterly (manual) | Re-run `batch_compare.py` + `feature_test.py` + `extract_test.py`; refresh `references/evidence.md` |
| On vendor announcement | Targeted re-test of the affected section only |

## Refresh procedure

1. Run the scripts (see `tests/README.md` for costs):
   `python tests/batch_compare.py` etc.
2. Update `references/evidence.md`: replace drifted numbers, **bump the
   "as of" dates**, and note what changed (don't silently rewrite history).
3. If a routing rule in `SKILL.md` no longer matches the evidence, change
   the rule and say why in the CHANGELOG.
4. Update `SKILL.md` frontmatter `metadata.version` and `CHANGELOG.md`,
   commit, tag.

## Versioning (semver)

- **Patch** (1.0.x): data refresh, numbers updated, rules unchanged
- **Minor** (1.x.0): new routing rules, new references, rule refinements
  backed by new evidence
- **Major** (x.0.0): a headline conclusion reversed (e.g. "fast mode is now
  good", "Exa wins Chinese content") — README positioning may need rewording

## CI drift check

`.github/workflows/drift-check.yml` runs `tests/smoke_test.py` monthly and on
demand. To enable:

1. Repo → Settings → Secrets and variables → Actions
2. Add `TAVILY_API_KEY` and `EXA_API_KEY`
3. Actions → drift-check → Run workflow (first run validates the setup)

Without secrets the workflow skips gracefully (green, no-op). A red run
means a documented fact drifted — open an issue from it, re-test, refresh.
