"""Parse nginx or Apache access logs (common and combined format) into a CSV file."""
import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path

LINE = re.compile(
    r'^(?P<ip>\S+) (?P<ident>\S+) (?P<user>\S+) \[(?P<time>[^\]]+)\] '
    r'"(?P<request>(?:[^"\\]|\\.)*)" (?P<status>\d{3}) (?P<bytes>\S+)'
    r'(?: "(?P<referrer>(?:[^"\\]|\\.)*)" "(?P<agent>(?:[^"\\]|\\.)*)")?')
REQUEST = re.compile(r"^(?P<method>[A-Z]+) (?P<path>\S+)(?: (?P<protocol>HTTP/[\d.]+))?$")
COLUMNS = ["time", "ip", "method", "path", "protocol", "status", "bytes", "referrer", "user_agent",
           "user"]


def clean(value):
    """Access logs write a dash where a value is missing; use an empty string instead."""
    return "" if value in (None, "-") else value


def parse_line(line):
    """Return a dict for one log line, or None if it isn't in common/combined format."""
    match = LINE.match(line.strip())
    if not match:
        return None
    try:
        when = datetime.strptime(match["time"], "%d/%b/%Y:%H:%M:%S %z").isoformat()
    except ValueError:
        return None
    request = REQUEST.match(match["request"])
    sent = match["bytes"]
    return {"time": when, "ip": match["ip"],
            "method": request["method"] if request else "",
            "path": request["path"] if request else clean(match["request"]),
            "protocol": (request["protocol"] or "") if request else "",
            "status": int(match["status"]), "bytes": int(sent) if sent.isdigit() else 0,
            "referrer": clean(match["referrer"]), "user_agent": clean(match["agent"]),
            "user": clean(match["user"])}


def wanted(row, status, path_contains, method):
    if status:
        text = str(row["status"])
        if not (text == status or (status.endswith("xx") and text[0] == status[0])):
            return False
    if path_contains and path_contains not in row["path"]:
        return False
    return not method or row["method"] == method.upper()


def read_rows(paths, status=None, path_contains=None, method=None):
    """Return (rows that match the filters, count of lines that couldn't be parsed)."""
    rows, bad = [], 0
    for path in paths:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = parse_line(line)
                if row is None:
                    bad += 1
                elif wanted(row, status, path_contains, method):
                    rows.append(row)
    return rows, bad


def main(argv=None):
    parser = argparse.ArgumentParser(description="Convert access logs to CSV.")
    parser.add_argument("files", nargs="+", type=Path, help="access log file(s)")
    parser.add_argument("--out", type=Path, help="write to this new CSV file instead of printing")
    parser.add_argument("--status", help="only this status (404) or class (5xx)")
    parser.add_argument("--path-contains", help="only requests whose path contains this text")
    parser.add_argument("--method", help="only this HTTP method, e.g. POST")
    parser.add_argument("--columns", default=",".join(COLUMNS),
                        help=f"columns to write, in order (default: {','.join(COLUMNS)})")
    args = parser.parse_args(argv)
    columns = [c.strip() for c in args.columns.split(",") if c.strip()]
    unknown = [c for c in columns if c not in COLUMNS]
    if unknown or not columns:
        parser.error(f"unknown column(s): {', '.join(unknown) or '(none given)'}; "
                     f"choose from {', '.join(COLUMNS)}")
    if args.status and not re.fullmatch(r"\d{3}|\dxx", args.status):
        parser.error("--status must look like 404 or 5xx")
    if args.out and args.out.exists():
        print(f"{args.out} already exists - pick a new name so nothing is overwritten.")
        return 1
    try:
        rows, bad = read_rows(args.files, args.status, args.path_contains, args.method)
    except OSError as err:
        print(f"Couldn't read the log: {err.strerror or err}", file=sys.stderr)
        return 1

    handle = args.out.open("w", newline="", encoding="utf-8") if args.out else sys.stdout
    try:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore",
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    finally:
        if args.out:
            handle.close()
    note = f"{len(rows)} row(s) written" + (f" to {args.out}" if args.out else "")
    print(note + (f"; {bad} line(s) weren't in access-log format and were skipped" if bad else "")
          + ".", file=sys.stderr if not args.out else sys.stdout)
    return 0 if rows else 1


if __name__ == "__main__":
    sys.exit(main())
