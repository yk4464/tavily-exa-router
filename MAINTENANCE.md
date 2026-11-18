# Maintenance

This repo's value is dated, reproducible evidence — which decays. This file
is the playbook for keeping it honest.

## What lives where

`SKILL.md` is the product: the rules an agent follows, and nothing else. It
carries no dates, no `references/…` paths, no `§n` anchors and no numbers
that exist only to justify a rule — the agent that loads it cannot follow any
of them, and they rot. Everything a maintainer needs lives beside it:

| File | Role |
|---|---|
| `references/evidence.md` | Measurements behind the rules, dated and sectioned (§1–§8) |
| `references/tavily.md` | Full Tavily parameter, endpoint and price reference |
| `references/exa.md` | Full Exa parameter, `contents`, `outputSchema` and price reference |
| `references/community-feedback.md` | Dated practitioner reports and provider issue trackers |
| `references/provider-api-audit-2026-08-18.md` | Dated official parameter and pricing audit (the 2026-08-18 baseline) |
| `tests/README.md` | Test kit: what each script measures, costs, and the eval fixtures |
| `CHANGELOG.md` | Why each rule changed, release by release |

`tests/validate_repo.py` enforces the split: it fails when `SKILL.md` gains a
date, a `references/…` link or a `§` anchor, when a document links a missing
`references/` file, when a `references/*.md` file is linked from none of
`SKILL.md`, the READMEs or the docs in this list, and when a `§n` citation has
no matching numbered heading.

## What rots, fastest first

1. **Prices, quotas, free tiers** — Exa already raised $5→$7/1k once
2. **Anti-block matrix** (which sites `/extract` vs `/contents` can fetch) —
   changes month to month
3. **Parameter names, modes, deprecations** — renamed or removed over time
4. **Quality/overlap conclusions** — index composition drifts slowly

## Cadence

| When | What |
|---|---|
| Monthly (automated) | `tests/smoke_test.py` via GitHub Actions — 14 live checks flag drift in load-bearing facts (~$0.062 + 4 Tavily credits per run) |
| Quarterly (manual) | Re-run `batch_compare.py`, `lite_quality_test.py` (Exa type defaults; evidence §7) and all `comprehensive_benchmark.py` suites; manually review the fixed quality queries; refresh `references/evidence.md` |
| On vendor announcement | Targeted re-test of the affected section only |
| On major SDK/MCP release | Re-check provider issue trackers and refresh `references/community-feedback.md` |

## Refresh procedure

1. Run the scripts (see `tests/README.md` for costs):
   `python tests/batch_compare.py` and the relevant comprehensive suites.
2. Inspect semantic evidence beyond HTTP status codes: domain constraints,
   per-URL failures, result fields, SSE completion, output-schema shape, cache
   state, login walls, and prompt-like instructions in fetched pages.
3. Manually review all fixed mode-query results. Allowlisted community and
   authority counts are heuristics and do not grade relevance alone.
4. Update `references/evidence.md`: replace drifted numbers, **bump "as of"
   dates**, and note changes without erasing history.
5. If a routing rule in `SKILL.md` no longer matches the evidence, change
   the rule and say why in the CHANGELOG. The date, the numbers and the
   sources stay in `references/evidence.md`; `SKILL.md` gets the rule only.
6. Update `SKILL.md` frontmatter `metadata.version` and `CHANGELOG.md`,
   commit, tag.

## Versioning (semver)

- **Patch** (1.0.x): data refresh, numbers updated, rules unchanged
- **Minor** (1.x.0): new routing rules, new references, rule refinements
  backed by new evidence
- **Major** (x.0.0): a headline conclusion reversed (e.g. "fast mode is now
  good", "Tavily wins Chinese content") — README positioning may need rewording

## CI drift check

`.github/workflows/drift-check.yml` runs on two cadences:

| Trigger | Jobs |
|---|---|
| Every push and pull request | `validate` — `tests/validate_repo.py` only |
| Monthly (1st, 03:00 UTC) and manual dispatch | `validate` + `smoke` — adds `tests/smoke_test.py` |

`validate` is secret-free, so it also runs on pull requests from forks: it
checks frontmatter shape, personal-path/API-key leaks, version claims,
reference/section consistency, and that `SKILL.md` stays rule-only (no dates,
no `references/…` paths, no `§` anchors). To enable the live provider checks:

1. Repo → Settings → Secrets and variables → Actions
2. Add `TAVILY_API_KEY` and `EXA_API_KEY`
3. Actions → drift-check → Run workflow (first run validates the setup)

Without secrets, `tests/smoke_test.py` emits a `::warning::` annotation on the
run page (which secrets are missing) and still exits 0, so the `smoke` job
stays green.

A red `smoke` run is one of two things — read the exit code (the workflow turns
it into a matching annotation):

| Exit | Meaning | What to do |
|---|---|---|
| 0 | All checks passed, or skipped for missing keys | Nothing |
| 1 | Fact drift | Open an issue, re-test the drifted facts, then update `SKILL.md` and `references/` |
| 2 | Infrastructure only (network, rate limit, 401/403) | Re-run first; only treat it as drift if it reproduces |

The `validate` job is untouched by vendor outages: it fails only on repository
defects.
