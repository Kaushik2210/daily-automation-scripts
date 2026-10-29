"""Rebuild the README index and tick finished items in PLAN.md.

A script counts as done when scripts/<category>/<name>/<name_with_underscores>.py exists.
"""
import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
START, END = "<!-- INDEX:START -->", "<!-- INDEX:END -->"
DAY_RE = re.compile(r"^## Day (\d\d) - ")
ITEM_RE = re.compile(r"^- \[[ x]\] (\d\d)\. (\S+) - .+ \(([a-z-]+)\)$")


def parse_plan(lines):
    day = None
    for i, line in enumerate(lines):
        m = DAY_RE.match(line)
        if m:
            day = m.group(1)
            continue
        m = ITEM_RE.match(line)
        if m and day:
            yield i, day, m.group(1), m.group(2), m.group(3)


def is_done(name, cat):
    folder = ROOT / "scripts" / cat / name
    return (folder / f"{name.replace('-', '_')}.py").is_file()


def main():
    parser = argparse.ArgumentParser(description="Regenerate the README index and PLAN.md checkboxes.")
    parser.parse_args()

    plan_path = ROOT / "PLAN.md"
    lines = plan_path.read_text(encoding="utf-8").splitlines()
    rows, total = [], 0
    for i, day, num, name, cat in parse_plan(lines):
        total += 1
        done = is_done(name, cat)
        lines[i] = lines[i].replace("- [ ]", "- [x]") if done else lines[i].replace("- [x]", "- [ ]")
        if done:
            link = f"[{name}](scripts/{cat}/{name}/)"
            rows.append(f"| {day} | {num} | {name} | {cat} | {link} |")
    plan_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    table = ["| Day | # | Script | Category | Link |", "| --- | --- | --- | --- | --- |", *rows]
    block = f"{START}\n\n**Progress: {len(rows)}/{total} done**\n\n" + "\n".join(table) + f"\n\n{END}"

    readme_path = ROOT / "README.md"
    text = readme_path.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text):
        raise SystemExit("README.md is missing the INDEX markers")
    readme_path.write_text(pattern.sub(lambda _: block, text), encoding="utf-8")
    print(f"{len(rows)}/{total} done")


if __name__ == "__main__":
    main()
