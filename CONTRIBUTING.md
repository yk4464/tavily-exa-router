# Contributing

PRs welcome. This repo's value is traceable, reproducible evidence — keep it honest.

**Most valuable contribution:** Re-testing existing rules against live APIs with scripts in `tests/` (costs listed in `tests/README.md`) to catch drift.

## Ground rules

- **Rules and evidence live apart.** `SKILL.md` is the product: an agent reads it and nothing else, so it states rules only — no dates, no `references/…` links, no `§n` anchors, no measurement numbers, no proof-by-example. Measurements, dates and sources go to `references/evidence.md`; why a rule changed goes to `CHANGELOG.md`. `tests/validate_repo.py` fails a `SKILL.md` that carries a date, a `references/…` path or a `§` anchor.
- **Evidence first**: a routing-rule change must ship with fresh measurements (re-run the relevant `tests/` scripts) recorded in `references/evidence.md`, or with a cited source added to `references/community-feedback.md`. The rule in `SKILL.md` states the conclusion, not the run.
- **Pricing & parameters**: record the verification date and the official vendor link in `references/evidence.md` (or `references/tavily.md` / `references/exa.md`). Quote the resulting figure in `SKILL.md` only when it changes what the agent sends.
- **USD syntax**: never write `$` followed by a digit in `SKILL.md` (e.g. `$0.007`) — skill loaders treat `$0`-style tokens as placeholders and strip them. Use `USD 0.007` instead. `tests/validate_repo.py` enforces this.

## Pre-submission checklist

Run these checks before opening a PR:

1. [ ] `python tests/validate_repo.py` passes all checks locally (zero cost, stdlib only).
2. [ ] Docs parity: changes to `README.md` (Chinese) are mirrored in `README_EN.md` (English) with matching sections, tables, and facts.
3. [ ] Skill-rule parity: every README sentence that describes skill behavior must match `SKILL.md`, which is the normative text for rules; every number, date or source in the READMEs must match `references/evidence.md`. The READMEs may explain and illustrate the rules, never contradict them or quote stale figures.
4. [ ] Evidence & changelog: rule changes cite their measurement or source in `references/evidence.md`, the rationale is in `CHANGELOG.md`, and the eval count in `tests/README.md` matches `evals/evals.json`.
5. [ ] Semver alignment: version bumps follow `MAINTENANCE.md` across all 4 locations:
   - `SKILL.md` frontmatter (`metadata.version`)
   - `README.md` header badge
   - `README_EN.md` header badge
   - `CHANGELOG.md` latest heading
6. [ ] No `$0` placeholders: verified no `$`+digit patterns introduced into `SKILL.md`.
