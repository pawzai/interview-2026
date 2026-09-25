"""Consistency check for a pack: question numbering, difficulty tags and answer coverage.

Usage:
    python tools/check-pack.py 07-devops
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def check(pack):
    d = ROOT / pack
    lines = (d / "questions.md").read_text(encoding="utf-8").splitlines()

    cats = []
    nums = []
    untagged = []
    in_category = False

    for raw in lines:
        s = raw.strip()
        m = re.match(r"^##\s+(\d+)\.\s+(.*)$", s)
        if m:
            cats.append((int(m.group(1)), m.group(2)))
            in_category = True
            continue
        m = re.match(r"^(\d+)\.\s+(.*)$", s)
        if m and in_category:
            nums.append(int(m.group(1)))
            if not re.match(r"^`\[[CDTA]\]`", m.group(2)):
                untagged.append(int(m.group(1)))

    print(f"{pack}: {len(nums)} questions across {len(cats)} categories")
    expected = list(range(1, len(nums) + 1))
    if nums != expected:
        missing = sorted(set(expected) - set(nums))
        dupes = sorted({n for n in nums if nums.count(n) > 1})
        print(f"  NUMBERING BROKEN  missing={missing[:20]} duplicated={dupes[:20]}")
    else:
        print(f"  numbering contiguous 1-{len(nums)}")
    if untagged:
        print(f"  UNTAGGED: {untagged}")

    answers_path = d / "answers.md"
    if answers_path.exists():
        answered = {
            int(m.group(1))
            for m in re.finditer(
                r"^###\s+Q(\d+)\.", answers_path.read_text(encoding="utf-8"), re.M
            )
        }
        dangling = sorted(answered - set(nums))
        print(f"  answers.md covers {len(answered)} questions")
        gaps = [n for n in nums if n not in answered]
        if gaps:
            print(f"  no scripted answer: {gaps}")
        if dangling:
            print(f"  ANSWERS WITH NO QUESTION: {dangling}")

    scen_path = d / "scenario-questions.md"
    if scen_path.exists():
        text = scen_path.read_text(encoding="utf-8")
        refs = sorted(int(m) for m in re.findall(r"^###\s+S\d+\..*\(Q(\d+)\)", text, re.M))
        print(f"  scenario cross-references: {refs}")
        bad = [r for r in refs if r not in nums]
        if bad:
            print(f"  BROKEN SCENARIO REFS: {bad}")


if __name__ == "__main__":
    for name in sys.argv[1:] or ["07-devops"]:
        check(name)
