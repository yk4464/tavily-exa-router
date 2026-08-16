"""Spec + leak checks for the tavily-exa-router skill."""
import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent  # repo root
content = (root / "SKILL.md").read_text(encoding="utf-8")

m = re.match(r"^---\n(.*?)\n---", content, re.S)
fm = m.group(1) if m else ""
name = re.search(r"name:\s*(\S+)", fm)
desc = re.search(r"description:\s*>?\s*\n((?:[ \t]+.*\n?)+)", fm)
print(f"name field: {name.group(1) if name else 'MISSING'} | dir: tavily-exa-router | match: {name and name.group(1) == 'tavily-exa-router'}")
if desc:
    d = " ".join(l.strip() for l in desc.group(1).splitlines())
    print(f"description: {len(d)} chars (limit 1024) -> {'OK' if len(d) <= 1024 else 'TOO LONG'}")
    print(f"  style: {'Use when/whenever present' if 'Use when' in d or 'whenever' in d else 'CHECK STYLE'}")

# leak check across all files
patterns = ["C:\\Users", "/Users/", "/home/", "Administrator", "zcode", "ZCode",
            "TAVILY_API_KEY=sk", "EXA_API_KEY="]
clean = True
for f in sorted(root.rglob("*")):
    if f.is_file():
        t = f.read_text(encoding="utf-8", errors="ignore")
        for pat in patterns:
            if pat in t:
                print(f"LEAK in {f.relative_to(root)}: {pat!r}")
                clean = False
print("leak check:", "CLEAN" if clean else "ISSUES FOUND")

# referenced files exist
refs = re.findall(r"`?references/([\w.-]+\.md)`?", content)
for r in set(refs):
    p = root / "references" / r
    print(f"reference references/{r}: {'exists' if p.exists() else 'MISSING'}")
