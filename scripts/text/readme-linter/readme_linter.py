"""Check a README for missing sections and common mistakes, and score it."""
import argparse
import re
import sys
from pathlib import Path

SECTIONS = [  # (label, regex for acceptable headings, weight, is it important?)
    ("Install", r"install|setup|getting started|requirements", 15, True),
    ("Usage", r"usage|example|quick ?start|how to", 20, True),
    ("License", r"licen[sc]e", 10, True),
    ("Contributing", r"contribut", 5, False),
    ("Features or overview", r"feature|overview|about|why|what", 5, False),
]
FENCE = re.compile(r"^\s*(```|~~~)")


def analyse(text):
    """Return (list of (status, message), score 0-100)."""
    lines = text.splitlines()
    headings, in_fence, fences, issues = [], False, 0, []
    for number, line in enumerate(lines, 1):
        if FENCE.match(line):
            in_fence = not in_fence
            fences += 1 if in_fence else 0
        elif not in_fence:
            match = re.match(r"^(#{1,6})\s+(.*?)\s*#*$", line)
            if match:
                headings.append((len(match.group(1)), match.group(2), number))
    score = 0

    def add(status, message, points=0):
        nonlocal score
        issues.append((status, message))
        score += points

    h1 = [h for h in headings if h[0] == 1]
    if not h1:
        add("FAIL", "No title: start with a single '# Project name' heading")
    elif len(h1) > 1:
        add("WARN", f"{len(h1)} top-level headings; a README should have one title", 5)
    else:
        add("PASS", f"Title: {h1[0][1]}", 10)
    words = len(re.findall(r"\w+", text))
    first = next((row for row in lines[(h1[0][2] if h1 else 0):] if row.strip()
                  and not row.startswith(("#", "!", "[!", "<", "[")) and not FENCE.match(row)),
                 "")
    if len(first.split()) >= 6:
        add("PASS", "Opens with a description of what the project is", 10)
    else:
        add("FAIL", "No short description under the title (what is this and who is it for?)")
    for label, pattern, weight, important in SECTIONS:
        if any(re.search(pattern, text_, re.IGNORECASE) for _, text_, _ in headings):
            add("PASS", f"Has the {label.lower()} section", weight)
        else:
            add("FAIL" if important else "WARN", f"Missing the {label.lower()} section")
    if fences:
        add("PASS", f"{fences} code example(s)", 10)
    else:
        add("WARN", "No code blocks: show a command or snippet people can copy")
    levels = [h[0] for h in headings]
    jumps = [headings[i][1] for i in range(1, len(headings)) if levels[i] > levels[i - 1] + 1]
    if jumps:
        add("WARN", f"Heading level skipped before: {', '.join(jumps[:3])}")
    else:
        add("PASS", "Heading levels are in order", 5)
    names = [h[1].lower() for h in headings]
    repeated = sorted({n for n in names if names.count(n) > 1})
    if repeated:
        add("WARN", f"Duplicate headings: {', '.join(repeated)}")
    empty = re.findall(r"\[[^\]]*\]\(\s*\)", text)
    if empty:
        add("FAIL", f"{len(empty)} link(s) with an empty address")
    todo = re.findall(r"\b(TODO|FIXME|TBD|lorem ipsum)\b", text, re.IGNORECASE)
    if todo:
        add("WARN", f"Placeholder text left in ({', '.join(sorted({t.upper() for t in todo}))})")
    else:
        add("PASS", "No TODO/placeholder text", 5)
    if words < 80:
        add("WARN", f"Only {words} words; most READMEs need more detail")
    else:
        add("PASS", f"{words} words", 5)
    if words > 400 and not any(re.search(r"contents|toc", h[1], re.IGNORECASE) for h in headings):
        add("WARN", "Long README without a table of contents")
    return issues, min(score, 100)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Lint a README file.")
    parser.add_argument("readme", type=Path, help="README.md to check")
    parser.add_argument("--min-score", type=int, default=60,
                        help="exit with 1 below this score (60)")
    args = parser.parse_args(argv)
    if not args.readme.is_file():
        parser.error(f"not a file: {args.readme}")
    issues, score = analyse(args.readme.read_text(encoding="utf-8", errors="replace"))
    print(f"{args.readme.name}: score {score}/100\n")
    for status, message in issues:
        print(f"  [{status}] {message}")
    failed = sum(status == "FAIL" for status, _ in issues)
    print(f"\n{failed} problem(s), {sum(s == 'WARN' for s, _ in issues)} suggestion(s).")
    return 1 if score < args.min_score or failed else 0


if __name__ == "__main__":
    sys.exit(main())
