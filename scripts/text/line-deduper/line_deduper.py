"""Remove duplicate lines from a file while keeping the original order."""
import argparse
import sys
from pathlib import Path


def dedupe_lines(lines, ignore_case=False, strip=False):
    """Return lines without repeats; the first occurrence of each is kept."""
    seen = set()
    result = []
    for line in lines:
        key = line.strip() if strip else line
        if ignore_case:
            key = key.lower()
        if key not in seen:
            seen.add(key)
            result.append(line)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Remove duplicate lines, keeping order.")
    parser.add_argument("file", type=Path, nargs="?", help="input file (default: stdin)")
    parser.add_argument("-i", "--ignore-case", action="store_true", help="compare ignoring case")
    parser.add_argument("--strip", action="store_true", help="ignore surrounding whitespace")
    parser.add_argument("-o", "--output", type=Path, help="write to this file instead of stdout")
    args = parser.parse_args(argv)

    text = args.file.read_text(encoding="utf-8") if args.file else sys.stdin.read()
    lines = text.splitlines()
    kept = dedupe_lines(lines, args.ignore_case, args.strip)
    result = "\n".join(kept) + ("\n" if kept else "")
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    else:
        sys.stdout.write(result)
    print(f"Removed {len(lines) - len(kept)} duplicate line(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
