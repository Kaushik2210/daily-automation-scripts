"""Show the differences between two text files, with optional colour."""
import argparse
import difflib
import sys
from pathlib import Path

COLORS = {"+": "\033[32m", "-": "\033[31m", "@": "\033[36m"}
RESET = "\033[0m"


def make_diff(old, new, old_name="old", new_name="new", context=3):
    """Return unified diff lines (without trailing newlines)."""
    return list(difflib.unified_diff(old.splitlines(), new.splitlines(), old_name, new_name,
                                     n=context, lineterm=""))


def colorize(line):
    if line.startswith(("+++", "---")):
        return f"\033[1m{line}{RESET}"
    color = COLORS.get(line[:1])
    return f"{color}{line}{RESET}" if color else line


def similarity(old, new):
    return difflib.SequenceMatcher(None, old, new).ratio()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Show a diff of two text files.")
    parser.add_argument("old", type=Path)
    parser.add_argument("new", type=Path)
    parser.add_argument("-c", "--context", type=int, default=3, help="lines of context")
    parser.add_argument("--color", choices=["auto", "always", "never"], default="auto")
    parser.add_argument("--exit-code", action="store_true",
                        help="exit with 1 when the files differ (like diff)")
    args = parser.parse_args(argv)
    for path in (args.old, args.new):
        if not path.is_file():
            parser.error(f"not a file: {path}")

    old = args.old.read_text(encoding="utf-8", errors="replace")
    new = args.new.read_text(encoding="utf-8", errors="replace")
    diff = make_diff(old, new, str(args.old), str(args.new), args.context)
    if not diff:
        print("The files are identical.")
        return 0
    use_color = args.color == "always" or (args.color == "auto" and sys.stdout.isatty())
    for line in diff:
        print(colorize(line) if use_color else line)
    print(f"\n{similarity(old, new):.0%} similar")
    return 1 if args.exit_code else 0


if __name__ == "__main__":
    sys.exit(main())
