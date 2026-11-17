"""Build a glossary from the **bold** terms and their definitions in markdown notes."""
import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path

DEFINITION = re.compile(r"^\s*(?:[-*+]\s+)?\*\*([^*]+?)\*\*\s*(?::|\s[-–—]\s)\s*(.+?)\s*$")
BOLD = re.compile(r"\*\*([^*]+?)\*\*")
FENCE = re.compile(r"^\s*(```|~~~)")


def extract(text):
    """Return (definitions {term: [definition, ...]}, [bold terms with no definition])."""
    definitions, others, in_fence = {}, [], False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = DEFINITION.match(line)
        if match:
            definitions.setdefault(match.group(1).strip().rstrip(":"), []).append(match.group(2))
            continue
        others += [term.strip() for term in BOLD.findall(line)]
    for term in definitions:  # a term used in prose elsewhere is not "undefined"
        others = [o for o in others if o.lower() != term.lower()]
    return definitions, list(dict.fromkeys(others))


def merge(found):
    """Case-insensitive merge: keep the first definition, remember how many there were."""
    merged = {}
    for term, defs in found.items():
        key = term.lower()
        if key in merged:
            merged[key]["count"] += len(defs)
        else:
            merged[key] = {"term": term, "definition": defs[0], "count": len(defs)}
    return sorted(merged.values(), key=lambda entry: entry["term"].lower())


def render_markdown(entries, undefined):
    lines, letter = ["# Glossary", ""], ""
    for entry in entries:
        first = entry["term"][0].upper()
        if first != letter:
            letter = first
            lines += [f"## {letter}", ""]
        lines.append(f"**{entry['term']}**  \n{entry['definition']}\n")
    for term in undefined:
        lines.append(f"**{term}**  \n(no definition yet)\n")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build a glossary from bold terms in notes.")
    parser.add_argument("notes", nargs="+", type=Path, help="markdown note files")
    parser.add_argument("--format", choices=["md", "csv", "json"], default="md")
    parser.add_argument("--include-undefined", action="store_true",
                        help="also list bold terms that have no definition")
    parser.add_argument("-o", "--output", type=Path, help="write to this file (default: print)")
    args = parser.parse_args(argv)

    definitions, undefined = {}, []
    for path in args.notes:
        if not path.is_file():
            parser.error(f"not a file: {path}")
        found, other = extract(path.read_text(encoding="utf-8", errors="replace"))
        for term, defs in found.items():
            definitions.setdefault(term, []).extend(defs)
        undefined += other
    entries = merge(definitions)
    known = {e["term"].lower() for e in entries}
    undefined = [t for t in dict.fromkeys(undefined) if t.lower() not in known]
    if not entries:
        print("No definitions found. Write them like **Term**: what it means.", file=sys.stderr)
        return 1

    extra = undefined if args.include_undefined else []
    if args.format == "md":
        text = render_markdown(entries, extra)
    elif args.format == "json":
        rows = [{"term": e["term"], "definition": e["definition"]} for e in entries]
        rows += [{"term": t, "definition": ""} for t in extra]
        text = json.dumps(rows, indent=1, ensure_ascii=False) + "\n"
    else:
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(["term", "definition"])
        writer.writerows([e["term"], e["definition"]] for e in entries)
        writer.writerows([t, ""] for t in extra)
        text = buffer.getvalue()
    if args.output:
        if args.output.exists():
            print(f"{args.output} already exists; choose another name.", file=sys.stderr)
            return 1
        args.output.write_text(text, encoding="utf-8")
        print(f"Saved {len(entries)} term(s) to {args.output}.")
    else:
        print(text, end="")
    repeats = sum(1 for e in entries if e["count"] > 1)
    notes = []
    if repeats:
        notes.append(f"{repeats} term(s) were defined more than once (first definition kept)")
    if undefined and not args.include_undefined:
        notes.append(f"{len(undefined)} bold term(s) have no definition (use --include-undefined)")
    if notes:
        print("\n" + "; ".join(notes) + ".", file=sys.stderr if args.output else sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
