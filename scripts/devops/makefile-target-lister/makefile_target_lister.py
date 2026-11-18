"""List the targets of a Makefile with their descriptions, grouped by ##@ section headings."""
import argparse
import re
import sys
from pathlib import Path

RULE = re.compile(r"^(?P<targets>[A-Za-z0-9_][^\s:=#%$]*(?:\s+[A-Za-z0-9_][^\s:=#%$]*)*)\s*:(?!=)"
                  r"\s*(?P<rest>.*)$")


def parse(text):
    """Return (list of target dicts, set of .PHONY names)."""
    targets, phony, section, comment = [], set(), "", []
    for number, raw in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
        line = raw.rstrip()
        section_match = re.match(r"^##@\s*(.+)$", line)
        if section_match:
            section, comment = section_match.group(1).strip(), []
            continue
        if re.match(r"^\.PHONY\s*:", line):
            phony.update(line.split(":", 1)[1].split())
            comment = []
            continue
        if line.startswith("#") and not line.startswith("##@"):
            comment.append(line.lstrip("#").strip())
            continue
        match = RULE.match(line)
        if match and not raw.startswith("\t"):
            rest = match.group("rest")
            deps, _, doc = rest.partition("##")
            description = doc.strip() or " ".join(comment).strip()
            for name in match.group("targets").split():
                if name.startswith("."):
                    continue
                targets.append({"name": name, "deps": deps.split("#")[0].split(),
                                "doc": description, "section": section, "line": number})
        comment = []
    return targets, phony


def main(argv=None):
    parser = argparse.ArgumentParser(description="List the documented targets of a Makefile.")
    parser.add_argument("makefile", type=Path, nargs="?", default=Path("Makefile"))
    parser.add_argument("--all", action="store_true", help="also list undocumented targets")
    args = parser.parse_args(argv)
    if not args.makefile.is_file():
        parser.error(f"not a file: {args.makefile}")

    targets, phony = parse(args.makefile.read_text(encoding="utf-8", errors="replace"))
    shown = [t for t in targets if t["doc"] or args.all]
    if not shown:
        print("No documented targets. Add '## description' after a target, e.g. "
              "'test: ## Run the tests'.", file=sys.stderr)
        return 1
    width = max(len(t["name"]) for t in shown)
    current = None
    for target in shown:
        if target["section"] != current:
            current = target["section"]
            print(f"\n{current}" if current else "")
        extra = f"  (needs: {', '.join(target['deps'])})" if target["deps"] else ""
        note = "" if target["name"] in phony or not phony else "  [file target]"
        print(f"  {target['name']:<{width}}  {target['doc'] or '(no description)'}{extra}{note}")
    hidden = len(targets) - len(shown)
    print(f"\n{len(shown)} target(s) listed" + (f", {hidden} without a description hidden "
                                                f"(use --all)." if hidden else "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
