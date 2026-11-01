"""Spec + leak checks for the tavily-exa-router skill."""
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent  # repo root
content = (root / "SKILL.md").read_text(encoding="utf-8")
errors = []
warnings = []


def read_text(path):
    return path.read_text(encoding="utf-8", errors="ignore")


m = re.match(r"^---\r?\n(.*?)\r?\n---", content, re.S)
fm = m.group(1) if m else ""
fm_lines = fm.splitlines()


def scalar_value(key):
    """Parse one frontmatter scalar as ("ok" | "missing" | "unparsed", text).

    Block scalars (`>` and `|`, with chomping and indentation indicators),
    quoted scalars and plain multi-line scalars are all accepted, so a valid
    YAML spelling never reads as a missing value.
    """
    start = next((i for i, line in enumerate(fm_lines)
                  if re.match(rf"^{re.escape(key)}\s*:", line)), -1)
    if start < 0:
        return "missing", ""
    head = fm_lines[start].split(":", 1)[1].strip()
    body = []
    for line in fm_lines[start + 1:]:
        if line.strip() and not line[0].isspace():
            break
        body.append(line)
    if not head:
        return "unparsed", ""
    indicator = re.match(r"^([>|])([+-]?\d*)\s*(?:#.*)?$", head)
    if indicator:
        indents = [len(line) - len(line.lstrip()) for line in body if line.strip()]
        cut = min(indents) if indents else 0
        chunk = [line[cut:] if line.strip() else "" for line in body]
        while chunk and not chunk[-1].strip():
            chunk.pop()
        text = "\n".join(chunk)
        if indicator.group(1) == ">":
            text = re.sub(r"(?<=\S)\n(?=\S)", " ", text)
        return ("ok", text) if text.strip() else ("unparsed", "")
    if head[0] in "\"'":
        quote = head[0]
        joined = " ".join([head] + [line.strip() for line in body]).strip()
        if len(joined) > 1 and joined.endswith(quote):
            return "ok", joined[1:-1].replace("\\n", "\n")
        return "unparsed", ""
    text = " ".join([head] + [line.strip() for line in body if line.strip()])
    return ("ok", text) if text else ("unparsed", "")


name_state, name_value = scalar_value("name")
name = name_value.strip() if name_state == "ok" else ""
name_format_ok = bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name))
dir_match = name == root.name
print(f"name field: {name or name_state.upper()} | format: "
      f"{'OK' if name_format_ok else 'INVALID'} | dir: {root.name} | match: {dir_match}")
if name_state == "unparsed":
    errors.append("frontmatter name cannot be parsed")
elif name_state == "missing":
    errors.append("frontmatter name is missing")
elif not name_format_ok:
    errors.append("frontmatter name must be lowercase letters, digits and single hyphens")
elif not dir_match:
    warnings.append(
        f"frontmatter name ({name}) differs from the checkout directory ({root.name}); "
        "normal for GitHub ZIP downloads, harmless otherwise")
    print(f"  WARN: skill name and directory name differ ({name} != {root.name})")

desc_state, desc_value = scalar_value("description")
if desc_state == "ok":
    d = " ".join(desc_value.split())
    desc_length_ok = len(d) <= 1024
    desc_style_ok = "Use when" in d or "whenever" in d
    print(f"description: {len(d)} chars (limit 1024) -> {'OK' if desc_length_ok else 'TOO LONG'}")
    print(f"  style: {'Use when/whenever present' if desc_style_ok else 'CHECK STYLE'}")
    if not desc_length_ok:
        errors.append("frontmatter description exceeds 1024 characters")
    if not desc_style_ok:
        errors.append("frontmatter description lacks trigger wording")
elif desc_state == "unparsed":
    print("description: UNPARSED (frontmatter has the key but its value cannot be read)")
    errors.append("frontmatter description cannot be parsed")
else:
    print("description: MISSING")
    errors.append("frontmatter description is missing")

# Placeholder safety: skill loaders expand $<digit> tokens as positional
# arguments, silently deleting prices like "$0.007" from the loaded body.
# Write "USD 0.007" instead. ($NAME-style env vars are unaffected.)
unsafe = [f"{i}: {line.strip()[:80]}" for i, line in enumerate(content.splitlines(), 1)
          if re.search(r"\$\d", line)]
print(f"placeholder-safe body (no $<digit>): {'OK' if not unsafe else 'VIOLATIONS'}")
for item in unsafe:
    print(f"  line {item}")
if unsafe:
    errors.append("SKILL.md contains $<digit> tokens that loaders expand away; use USD forms")

# Rule-only body: SKILL.md is the product an agent reads end to end, and it
# cannot follow a `references/...` path, a `§n` anchor or a date. Provenance
# belongs in references/evidence.md and the reasoning in CHANGELOG.md, so a
# re-added pointer or date is a defect rather than a detail. The frontmatter
# is scanned too: `metadata.evidence-tested` was a date sitting right there.
FORBIDDEN_IN_SKILL = (
    ("provenance link", re.compile(r"references/")),
    ("section anchor", re.compile(r"§")),
    ("date", re.compile(r"\b\d{4}-\d{2}-\d{2}\b")),
)
offences = []
body = content[m.end():] if m else content
first = content.count("\n", 0, m.end()) + 1 if m else 1
for label, pattern in FORBIDDEN_IN_SKILL:
    for i, line in enumerate(fm_lines, 2):  # line 1 is the opening ---
        if pattern.search(line):
            offences.append((label, i, line.strip()[:70]))
    for offset, line in enumerate(body.splitlines()):
        if pattern.search(line):
            offences.append((label, first + offset, line.strip()[:70]))
print(f"rule-only body (no references/, §, dates): {'OK' if not offences else 'VIOLATIONS'}")
for label, line_no, text in sorted(offences, key=lambda item: item[1]):
    print(f"  line {line_no} ({label}): {text}")
if offences:
    errors.append(
        "SKILL.md carries provenance or dates; keep it rules-only and put evidence in "
        "references/evidence.md, reasons in CHANGELOG.md")

# Leak check across every file that would be published: tracked and unignored
# files, all extensions. Binary files are skipped by content, not by suffix, so
# a stray shell script or .env is still scanned while results dumps are not.
# Patterns require a concrete username or credential value, so documentation
# placeholders and this file do not match.
PLACEHOLDERS = {
    "...", "<", "your_", "your-", "your", "changeme", "none", "null", "example",
    "placeholder", "redacted", "dummy", "xxx", "todo", "replace", "insert",
    "username", "user", "you", "name", "someone", "person",
}
patterns = {
    "Windows user path": re.compile(
        r"\b[A-Za-z]:[/\\]{1,2}Users[/\\]([^/\\\s\"'`<>]+)", re.I),
    "macOS user path": re.compile(r"(?<![\w:.~/\\])/Users/([^/\s\"'`<>]+)"),
    "Linux user path": re.compile(r"(?<![\w:.~/\\])/home/([^/\s\"'`<>]+)"),
    # Bare key shapes catch any occurrence (`export K=v`, `.env`, JSON/YAML,
    # prose) without depending on the variable name being written next to it.
    "Tavily API key": re.compile(r"\btvly-[A-Za-z0-9_-]{20,}"),
    "Exa API key": re.compile(
        r"[\"']?EXA_API_KEY[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9_-]{20,})"),
}
# URL path segments look exactly like home directories ("example.com/home/lab"),
# so strip URLs before matching rather than teaching each pattern about them.
URL = re.compile(r"\b(?:https?|ftp)://\S+|\bwww\.\S+"
                 r"|\b[\w-]+\.(?:com|org|net|io|dev|ai|co|cn)/\S*")


def git_visible_files():
    """Repo-relative paths git would publish, or None outside a git checkout."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others",
             "--exclude-standard"],
            capture_output=True, timeout=30, check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return {p for p in out.decode("utf-8", "ignore").split("\0") if p}


def ignore_patterns():
    path = root / ".gitignore"
    if not path.exists():
        return []
    return [line.strip() for line in read_text(path).splitlines()
            if line.strip() and not line.strip().startswith("#")]


IGNORE = ignore_patterns()


def ignored(rel):
    """Minimal .gitignore match, used when the checkout has no git metadata."""
    parts = rel.split("/")
    for pattern in IGNORE:
        dir_only = pattern.endswith("/")
        p = pattern.strip("/")
        if "/" not in p:
            candidates = parts[:-1] if dir_only else parts
            if any(fnmatch.fnmatchcase(part, p) for part in candidates):
                return True
        else:
            if rel.startswith(p.rstrip("/") + "/") or fnmatch.fnmatchcase(rel, p):
                return True
    return False


def binary(path):
    try:
        with path.open("rb") as fh:
            return b"\x00" in fh.read(8192)
    except OSError:
        return True


visible = git_visible_files()
self_path = Path(__file__).resolve()
clean = True
scanned = 0
for f in sorted(root.rglob("*")):
    if not f.is_file():
        continue
    rel = f.relative_to(root).as_posix()
    if ".git" in f.relative_to(root).parts or f.resolve() == self_path:
        continue
    if visible is not None:
        if rel not in visible:
            continue
    elif ignored(rel):
        continue
    if binary(f):
        continue
    scanned += 1
    t = URL.sub(" ", read_text(f))
    for label, pattern in patterns.items():
        for hit in pattern.finditer(t):
            # Ignore matches whose value is an obvious documentation stand-in.
            val = (hit.group(1) if hit.groups() else hit.group(0)).strip().strip("\"'").lower()
            if any(p in val for p in PLACEHOLDERS):
                continue
            line_no = t.count("\n", 0, hit.start()) + 1
            print(f"LEAK in {rel}:{line_no}: {label}")
            clean = False
print(f"leak check: {scanned} files scanned -> {'CLEAN' if clean else 'ISSUES FOUND'}")
if not clean:
    errors.append("possible personal path or API key found")

# Version consistency: the frontmatter is the single source of truth, and the
# README header line drifted three releases behind it once. Check the READMEs'
# *current-version* claim and the CHANGELOG's newest heading against it.
# Historical mentions (e.g. "As of v1.2.0, ...") are legitimate and ignored.
# Unreleased entries do not fail the check: they only mean a bump is pending.
ver = re.search(r"^\s*version:\s*[\"']?(\d+\.\d+\.\d+)", fm, re.M)
if ver:
    version = ver.group(1)
    print(f"version: frontmatter {version}")
    # Header claim, in either language: "当前版本 v1.3.4" / "Current version v1.3.4"
    current_claim = re.compile(r"(?:当前版本|Current version)\s*v(\d+\.\d+\.\d+)")
    for doc in ("README.md", "README_EN.md"):
        path = root / doc
        if not path.exists():
            continue
        m_claim = current_claim.search(read_text(path))
        if not m_claim:
            print(f"  {doc}: no current-version claim found")
            errors.append(f"{doc} has no 'current version' header claim to verify")
        elif m_claim.group(1) != version:
            print(f"  version mismatch in {doc}: header says v{m_claim.group(1)}")
            errors.append(
                f"{doc} header claims v{m_claim.group(1)} but frontmatter version is {version}")
        else:
            print(f"  {doc} header claim: v{m_claim.group(1)} -> OK")

    changelog = root / "CHANGELOG.md"
    if changelog.exists():
        ch_lines = read_text(changelog).splitlines()
        unreleased_entries = 0
        for i, line in enumerate(ch_lines):
            if re.fullmatch(r"##\s+\[?Unreleased\]?\s*", line, re.I):
                section = []
                for follow in ch_lines[i + 1:]:
                    if re.match(r"##\s", follow):
                        break
                    section.append(follow)
                bullets = [l for l in section if re.match(r"\s*(?:[-*+]|\d+\.)\s+\S", l)]
                unreleased_entries = len(bullets) or sum(1 for l in section if l.strip())
                break
        if unreleased_entries:
            print(f"  WARN: CHANGELOG.md has {unreleased_entries} entries under '## Unreleased' "
                  f"while frontmatter version is still {version} — version bump pending")
            warnings.append(
                f"CHANGELOG.md has {unreleased_entries} unreleased entries under '## Unreleased' "
                f"but frontmatter version is still {version}")
        headings = re.findall(r"^##\s+(\d+\.\d+\.\d+)", "\n".join(ch_lines), re.M)
        if headings and headings[0] != version:
            print(f"  version mismatch in CHANGELOG.md: newest heading is {headings[0]}")
            errors.append(
                f"CHANGELOG.md newest entry ({headings[0]}) != frontmatter version ({version})")
        elif headings:
            print(f"  CHANGELOG.md newest heading: {headings[0]} -> OK")
else:
    print("version: MISSING from frontmatter")
    errors.append("frontmatter metadata.version is missing")

# Skill eval fixture structure. The fixture names the skill, so it is tied to
# the frontmatter name rather than to whatever directory the ZIP unpacked into.
eval_path = root / "evals" / "evals.json"
if eval_path.exists():
    eval_data = None
    try:
        eval_data = json.loads(read_text(eval_path))
    except (OSError, json.JSONDecodeError):
        eval_data = None
    evals = (eval_data.get("evals") or []) if isinstance(eval_data, dict) else []
    eval_skill = eval_data.get("skill_name") if isinstance(eval_data, dict) else None
    eval_ok = (isinstance(eval_data, dict) and eval_skill == name and len(evals) >= 6
               and all(item.get("prompt") and item.get("expectations") for item in evals))
    print(f"skill evals: {len(evals)} cases -> {'OK' if eval_ok else 'INVALID'}")
    if isinstance(eval_data, dict) and eval_skill != name:
        print(f"  eval skill_name: {eval_skill or 'MISSING'} != frontmatter name {name or 'MISSING'}")
    if not eval_ok:
        errors.append("evals/evals.json is invalid or lacks coverage")
else:
    print("skill evals: MISSING")
    errors.append("evals/evals.json is missing")

# Reference links: every `references/*.md` a reader is sent to must exist, and
# every file in references/ must be reachable from a document that cites it —
# the skill the agent loads, a README, or a maintainer doc (SKILL.md no longer
# carries the list, so MAINTENANCE.md owns the reference map) — otherwise files
# rot in place unnoticed.
link_docs = ("SKILL.md", "README.md", "README_EN.md",
             "MAINTENANCE.md", "CONTRIBUTING.md", "tests/README.md")
linked = set()
for doc in link_docs:
    path = root / doc
    if not path.exists():
        continue
    for r in sorted(set(re.findall(r"references/([\w.-]+\.md)", read_text(path)))):
        linked.add(r)
        exists = (root / "references" / r).exists()
        print(f"reference from {doc}: references/{r} -> {'exists' if exists else 'MISSING'}")
        if not exists:
            errors.append(f"{doc} links a missing file: references/{r}")
refs_dir = root / "references"
if refs_dir.is_dir():
    for p in sorted(refs_dir.glob("*.md")):
        if p.name not in linked:
            print(f"reference references/{p.name}: not linked from any document")
            errors.append(
                f"references/{p.name} is not linked from SKILL.md, the READMEs "
                "or the maintainer docs")

# Section anchors: documents cite sections as "§3", "§4b", "§5.3"..., so each
# citation must still have a numbered heading in the reference file its line
# points at (evidence.md when the line is a wrapped continuation with no file
# mention). Anchors are per file because §1 of community-feedback.md is a
# different section from §1 of evidence.md. Every document that still writes
# § is scanned — SKILL.md loses its anchors with the rule-only trim, but the
# READMEs and the maintainer docs keep theirs.
numbered = {}
for path in sorted((root / "references").glob("*.md")):
    ids = set()
    for heading in re.findall(r"^#{1,6}\s+(\S+)", read_text(path), re.M):
        m_heading = re.match(r"^(\d+(?:\.\d+)*)([a-z]?)(?:[.\s:]|$)", heading)
        if m_heading:
            ids.add(m_heading.group(1) + m_heading.group(2))
    numbered[path.name] = ids
missing = []
unverifiable = []
for doc in link_docs:
    path = root / doc
    if not path.exists():
        continue
    for line in read_text(path).splitlines():
        for anchor in re.findall(r"§(\d+(?:\.\d+)*[a-z]?)", line):
            targets = re.findall(r"references/([\w.-]+\.md)", line) or ["evidence.md"]
            targets = [t for t in targets if t in numbered]  # a missing file is reported above
            if not targets:
                continue
            if any(anchor in numbered[t] for t in targets):
                continue
            if all(not numbered[t] for t in targets):
                item = (doc, "/".join(targets), anchor)
                if item not in unverifiable:
                    unverifiable.append(item)
                continue
            item = (doc, "/".join(t for t in targets if numbered.get(t)), anchor)
            if item not in missing:
                missing.append(item)
print(f"section anchors: {'OK' if not missing and not unverifiable else 'CHECK'}")
for doc, ref, anchor in missing:
    print(f"  {doc}: §{anchor}: references/{ref} has no such heading")
    errors.append(f"{doc} cites §{anchor} but references/{ref} has no such heading")
for doc, ref, anchor in unverifiable:
    print(f"  WARN: {doc} §{anchor} points at references/{ref}, which has no numbered headings")
    warnings.append(
        f"{doc} cites §{anchor} but references/{ref} has no numbered headings to verify it")

if errors:
    print("\nFAILED:")
    for error in errors:
        print(f"- {error}")
    if warnings:
        print("WARNINGS (not failures):")
        for warning in warnings:
            print(f"- {warning}")
    sys.exit(1)

if warnings:
    print("\nWARNINGS (not failures):")
    for warning in warnings:
        print(f"- {warning}")

print("\nAll repository checks passed.")
