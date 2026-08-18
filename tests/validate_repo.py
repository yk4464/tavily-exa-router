"""Spec + leak checks for the tavily-exa-router skill."""
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent  # repo root
content = (root / "SKILL.md").read_text(encoding="utf-8")
errors = []

m = re.match(r"^---\n(.*?)\n---", content, re.S)
fm = m.group(1) if m else ""
name = re.search(r"name:\s*(\S+)", fm)
desc = re.search(r"description:\s*>?\s*\n((?:[ \t]+.*\n?)+)", fm)
name_ok = bool(name and name.group(1) == root.name)
print(f"name field: {name.group(1) if name else 'MISSING'} | dir: {root.name} | match: {name_ok}")
if not name_ok:
    errors.append("frontmatter name does not match the repository directory")
if desc:
    d = " ".join(l.strip() for l in desc.group(1).splitlines())
    desc_length_ok = len(d) <= 1024
    desc_style_ok = "Use when" in d or "whenever" in d
    print(f"description: {len(d)} chars (limit 1024) -> {'OK' if desc_length_ok else 'TOO LONG'}")
    print(f"  style: {'Use when/whenever present' if desc_style_ok else 'CHECK STYLE'}")
    if not desc_length_ok:
        errors.append("frontmatter description exceeds 1024 characters")
    if not desc_style_ok:
        errors.append("frontmatter description lacks trigger wording")
else:
    print("description: MISSING")
    errors.append("frontmatter description is missing")

# Leak check across public text files. Patterns require a concrete username or
# credential value, so documentation placeholders and this file do not match.
patterns = {
    "Windows user path": re.compile(r"C:\\+Users\\+[^\\\s]+", re.I),
    "macOS user path": re.compile(r"/Users/[^/\s]+"),
    "Linux user path": re.compile(r"/home/[^/\s]+"),
    "Tavily API key": re.compile(r"TAVILY_API_KEY\s*=\s*[\"']?tvly-[A-Za-z0-9_-]{16,}"),
    "Exa API key": re.compile(r"EXA_API_KEY\s*=\s*[\"']?(?!\.\.\.|<)[A-Za-z0-9_-]{20,}"),
}
skip_dirs = {".git", "__pycache__", "node_modules", "search_results"}
text_suffixes = {".md", ".py", ".yml", ".yaml", ".txt", ".json", ".toml"}
clean = True
for f in sorted(root.rglob("*")):
    if (f.is_file() and f.suffix.lower() in text_suffixes
            and f.resolve() != Path(__file__).resolve()
            and not any(part in skip_dirs for part in f.relative_to(root).parts)):
        t = f.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in patterns.items():
            if pattern.search(t):
                print(f"LEAK in {f.relative_to(root)}: {label}")
                clean = False
print("leak check:", "CLEAN" if clean else "ISSUES FOUND")
if not clean:
    errors.append("possible personal path or API key found")

# Skill eval fixture structure
eval_path = root / "evals" / "evals.json"
if eval_path.exists():
    import json

    try:
        eval_data = json.loads(eval_path.read_text(encoding="utf-8"))
        evals = eval_data.get("evals") or []
        eval_ok = (eval_data.get("skill_name") == root.name and len(evals) >= 6
                   and all(item.get("prompt") and item.get("expectations") for item in evals))
    except (OSError, json.JSONDecodeError):
        eval_ok = False
    print(f"skill evals: {len(evals) if 'evals' in locals() else 0} cases -> {'OK' if eval_ok else 'INVALID'}")
    if not eval_ok:
        errors.append("evals/evals.json is invalid or lacks coverage")
else:
    print("skill evals: MISSING")
    errors.append("evals/evals.json is missing")

# referenced files exist
refs = re.findall(r"`?references/([\w.-]+\.md)`?", content)
for r in set(refs):
    p = root / "references" / r
    exists = p.exists()
    print(f"reference references/{r}: {'exists' if exists else 'MISSING'}")
    if not exists:
        errors.append(f"missing reference: references/{r}")

if errors:
    print("\nFAILED:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("\nAll repository checks passed.")
