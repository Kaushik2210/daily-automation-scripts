"""Rank the client IPs in a web access log by requests or bytes, and flag noisy ones."""
import argparse
import ipaddress
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

LINE = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] "(?P<request>(?:[^"\\]|\\.)*)" '
    r'(?P<status>\d{3}) (?P<bytes>\S+)')
REQUEST_PATH = re.compile(r"^[A-Z]+ (\S+)")


def parse_line(line):
    match = LINE.match(line.strip())
    if not match:
        return None
    try:
        when = datetime.strptime(match["time"], "%d/%b/%Y:%H:%M:%S %z")
    except ValueError:
        return None
    path = REQUEST_PATH.match(match["request"])
    return {"ip": match["ip"], "time": when, "status": int(match["status"]),
            "bytes": int(match["bytes"]) if match["bytes"].isdigit() else 0,
            "path": path.group(1) if path else ""}


def group_key(ip, prefix):
    """The address itself, or the network it belongs to (e.g. 203.0.113.0/24)."""
    if not prefix:
        return ip
    try:
        return str(ipaddress.ip_network(f"{ip}/{prefix}", strict=False))
    except ValueError:
        return ip


def human_size(size):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def tally(rows, prefix=None, skip=()):
    stats = defaultdict(lambda: {"requests": 0, "bytes": 0, "errors": 0, "first": None,
                                 "last": None, "paths": defaultdict(int)})
    for row in rows:
        if row["ip"] in skip:
            continue
        entry = stats[group_key(row["ip"], prefix)]
        entry["requests"] += 1
        entry["bytes"] += row["bytes"]
        entry["errors"] += row["status"] >= 400
        entry["first"] = min(entry["first"] or row["time"], row["time"])
        entry["last"] = max(entry["last"] or row["time"], row["time"])
        entry["paths"][row["path"]] += 1
    return stats


def ranked(stats, by="requests"):
    return sorted(stats.items(), key=lambda kv: (-kv[1][by], kv[0]))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Rank client IPs in an access log.")
    parser.add_argument("files", nargs="+", type=Path, help="access log file(s)")
    parser.add_argument("--top", type=int, default=10, help="how many to list (10)")
    parser.add_argument("--by", choices=["requests", "bytes", "errors"], default="requests")
    parser.add_argument("--network", type=int, metavar="BITS",
                        help="group IPs by network, e.g. 24 for IPv4 /24 blocks")
    parser.add_argument("--exclude-ip", action="append", default=[], metavar="IP",
                        help="leave out an address (yourself, monitoring); repeat for several")
    args = parser.parse_args(argv)
    if args.top < 1:
        parser.error("--top must be at least 1")
    if args.network is not None and not 1 <= args.network <= 128:
        parser.error("--network must be between 1 and 128")

    rows, bad = [], 0
    for path in args.files:
        try:
            with path.open(encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    row = parse_line(line)
                    if row:
                        rows.append(row)
                    else:
                        bad += 1
        except OSError as err:
            print(f"Couldn't read {path}: {err.strerror or err}", file=sys.stderr)
            return 1
    stats = tally(rows, args.network, set(args.exclude_ip))
    if not stats:
        print("No access-log requests found." + (f" ({bad} unreadable line(s))" if bad else ""))
        return 1

    total = sum(s["requests"] for s in stats.values())
    ranking = ranked(stats, args.by)
    print(f"{total:,} request(s) from {len(stats)} {'network' if args.network else 'IP'}(s)"
          + (f"; {bad} unreadable line(s) skipped" if bad else "") + f". Ranked by {args.by}.\n")
    width = max(len(name) for name, _ in ranking[:args.top])
    print(f"{'#':>3}  {'Address':<{width}}  {'Requests':>8}  {'Share':>6}  {'Data':>9}  "
          f"{'Errors':>6}")
    for place, (name, entry) in enumerate(ranking[:args.top], 1):
        share = entry["requests"] / total
        top_path = max(entry["paths"].items(), key=lambda kv: (kv[1], kv[0]))[0]
        noisy = (entry["requests"] >= 5 and entry["errors"] / entry["requests"] >= 0.5)
        flag = "  <-- mostly errors" if noisy else ""
        print(f"{place:>3}  {name:<{width}}  {entry['requests']:>8,}  {share:>6.1%}  "
              f"{human_size(entry['bytes']):>9}  {entry['errors']:>6}{flag}")
        print(f"       {entry['first']:%Y-%m-%d %H:%M} to {entry['last']:%H:%M}, "
              f"most requested: {top_path or '-'}")
    if len(ranking) > args.top:
        print(f"... and {len(ranking) - args.top} more.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
