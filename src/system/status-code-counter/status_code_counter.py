"""Count HTTP status codes in an access log and show which pages cause the errors."""
import argparse
import re
import sys
from collections import Counter, defaultdict
from http import HTTPStatus
from pathlib import Path

LINE = re.compile(r'^\S+ \S+ \S+ \[[^\]]+\] "(?P<request>(?:[^"\\]|\\.)*)" (?P<status>\d{3}) \S+')
REQUEST = re.compile(r"^(?P<method>[A-Z]+) (?P<path>\S+)")
CLASS_NAMES = {1: "informational", 2: "success", 3: "redirect", 4: "client error",
               5: "server error"}


def parse_line(line):
    match = LINE.match(line.strip())
    if not match:
        return None
    request = REQUEST.match(match["request"])
    path = request["path"].split("?", 1)[0] if request else ""
    return int(match["status"]), (request["method"] if request else ""), path


def reason(code):
    try:
        return HTTPStatus(code).phrase
    except ValueError:
        return "unknown"


def count(lines, method=None, path_contains=None):
    """Return (status counter, {status: path counter}, unreadable line count)."""
    codes, paths, bad = Counter(), defaultdict(Counter), 0
    for line in lines:
        if not line.strip():
            continue
        parsed = parse_line(line)
        if parsed is None:
            bad += 1
            continue
        status, verb, path = parsed
        if (method and verb != method.upper()) or (path_contains and path_contains not in path):
            continue
        codes[status] += 1
        paths[status][path or "(none)"] += 1
    return codes, paths, bad


def bar(value, biggest, width=24):
    return "#" * max(1, round(value / biggest * width))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Count HTTP status codes in an access log.")
    parser.add_argument("files", nargs="+", type=Path, help="access log file(s)")
    parser.add_argument("--method", help="only this HTTP method, e.g. POST")
    parser.add_argument("--path-contains", help="only requests whose path contains this text")
    parser.add_argument("--top-paths", type=int, default=3,
                        help="paths to list for each error code (3, use 0 to hide)")
    parser.add_argument("--fail-above-5xx", type=float, metavar="PERCENT",
                        help="exit with 1 if server errors are more than this percent of requests")
    args = parser.parse_args(argv)
    if args.top_paths < 0:
        parser.error("--top-paths can't be negative")

    lines = []
    for path in args.files:
        try:
            lines += path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as err:
            print(f"Couldn't read {path}: {err.strerror or err}", file=sys.stderr)
            return 1
    codes, paths, bad = count(lines, args.method, args.path_contains)
    total = sum(codes.values())
    if not total:
        print("No matching access-log requests found." + (f" ({bad} unreadable line(s))"
                                                           if bad else ""))
        return 1

    print(f"{total:,} request(s)" + (f"; {bad} unreadable line(s) skipped" if bad else "") + "\n")
    biggest = max(codes.values())
    print("By status code:")
    for code, number in sorted(codes.items()):
        print(f"  {code} {reason(code):<22} {number:>6,}  {number / total:>6.1%}  "
              f"{bar(number, biggest)}")
    classes = Counter()
    for code, number in codes.items():
        classes[code // 100] += number
    print("\nBy class:")
    for family in sorted(classes):
        print(f"  {family}xx {CLASS_NAMES.get(family, 'other'):<14} {classes[family]:>6,}  "
              f"{classes[family] / total:>6.1%}")
    errors = [code for code in sorted(codes) if code >= 400]
    if errors and args.top_paths:
        print("\nPaths behind the errors:")
        for code in errors:
            top = ", ".join(f"{p} ({n})" for p, n in paths[code].most_common(args.top_paths))
            print(f"  {code}: {top}")
    server_share = 100 * classes[5] / total
    print(f"\nClient errors: {100 * classes[4] / total:.1f}%   Server errors: {server_share:.1f}%")
    if args.fail_above_5xx is not None and server_share > args.fail_above_5xx:
        print(f"Server errors are above the limit of {args.fail_above_5xx:g}%.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
