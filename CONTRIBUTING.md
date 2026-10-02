# Contributing

PRs welcome. This repo's value is traceable, reproducible evidence — keep it honest.

**Most valuable contribution:** Re-testing existing rules against live APIs with scripts in `tests/` (costs listed in `tests/README.md`) to catch drift.

## Ground rules

- **Evidence first**: any rule change must include fresh measurements (re-run `tests/` scripts) or cited sources in `references/community-feedback.md`.
- **Pricing & parameters**: state the verification date and link directly to official vendor documentation.
- **USD syntax**: never write `$` followed by a digit in `SKILL.md` (e.g. `$0.007`) — skill loaders treat `$0`-style tokens as placeholders and strip them. Use `USD 0.007` instead. `tests/validate_repo.py` enforces this.

## Pre-submission checklist

Run these checks before opening a PR:

1. [ ] `python tests/validate_repo.py` passes all checks locally (zero cost, stdlib only).
2. [ ] Docs parity: changes to `README.md` (Chinese) are mirrored in `README_EN.md` (English) with matching sections, tables, and facts.
3. [ ] Evidence & changelog: updated rules or metrics include raw measurement data or cited sources, with rationale documented in `CHANGELOG.md`.
4. [ ] Semver alignment: version bumps follow `MAINTENANCE.md` across all 4 locations:
   - `SKILL.md` frontmatter (`metadata.version`)
   - `README.md` header badge
   - `README_EN.md` header badge
   - `CHANGELOG.md` latest heading
5. [ ] No `$0` placeholders: verified no `$`+digit patterns introduced into `SKILL.md`.
