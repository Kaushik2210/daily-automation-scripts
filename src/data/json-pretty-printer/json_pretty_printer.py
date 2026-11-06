"""Format, minify or validate JSON, with clear error positions."""
import argparse
import json
import sys
from pathlib import Path


def format_json(text, indent=2, sort_keys=False, minify=False):
    """Return formatted JSON text; raises json.JSONDecodeError if `text` is invalid."""
    data = json.loads(text)
    if minify:
        return json.dumps(data, separators=(",", ":"), sort_keys=sort_keys, ensure_ascii=False)
    return json.dumps(data, indent=indent, sort_keys=sort_keys, ensure_ascii=False)


def explain_error(err, text):
    """Point at the line that broke the parse."""
    line = text.splitlines()[err.lineno - 1] if text.splitlines() else ""
    pointer = " " * max(err.colno - 1, 0) + "^"
    return f"Invalid JSON: {err.msg} (line {err.lineno}, column {err.colno})\n{line}\n{pointer}"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Pretty-print, minify or validate JSON.")
    parser.add_argument("file", type=Path, nargs="?", help="JSON file (default: stdin)")
    parser.add_argument("--indent", type=int, default=2, help="spaces per level (default 2)")
    parser.add_argument("--sort-keys", action="store_true", help="sort object keys")
    parser.add_argument("--minify", action="store_true", help="remove all extra whitespace")
    parser.add_argument("--check", action="store_true", help="only validate, print nothing else")
    parser.add_argument("-o", "--output", type=Path, help="write the result to this file")
    parser.add_argument("--apply", action="store_true",
                        help="really write --output (default only previews it)")
    args = parser.parse_args(argv)

    text = args.file.read_text(encoding="utf-8-sig") if args.file else sys.stdin.read()
    try:
        result = format_json(text, args.indent, args.sort_keys, args.minify)
    except json.JSONDecodeError as err:
        print(explain_error(err, text), file=sys.stderr)
        return 1
    if args.check:
        print("Valid JSON.")
        return 0
    if args.output and args.apply:
        args.output.write_text(result + "\n", encoding="utf-8")
        print(f"Wrote {args.output}.")
    else:
        print(result)
        if args.output:
            print(f"(preview only: use --apply to write {args.output})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
