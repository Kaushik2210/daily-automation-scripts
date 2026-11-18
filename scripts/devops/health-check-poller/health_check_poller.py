"""Poll health-check URLs several times and report failures, slow responses and uptime."""
import argparse
import csv
import sys
import time
import urllib.error  # web-ok: URLs are only requested when polling; --summarise reads a saved CSV
import urllib.request
from datetime import datetime
from pathlib import Path

FIELDS = ["time", "url", "status", "ms", "ok", "error"]


def matches(status, expect):
    """expect is '200' or a class such as '2xx'."""
    if expect.lower().endswith("xx"):
        return str(status).startswith(expect[0])
    return str(status) == expect


def check(url, timeout, expect, contains):
    """Request the URL once. Return a dict with status, ms, ok and error."""
    started = time.perf_counter()
    status, error, body = 0, "", ""
    request = urllib.request.Request(url, headers={"User-Agent": "daily-automation-scripts/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            body = response.read(200_000).decode("utf-8", errors="replace") if contains else ""
    except urllib.error.HTTPError as err:
        status, error = err.code, f"HTTP {err.code}"
    except (urllib.error.URLError, OSError, ValueError) as err:
        error = str(getattr(err, "reason", err)) or err.__class__.__name__
    ms = round((time.perf_counter() - started) * 1000)
    ok = bool(status) and matches(status, expect) and not error
    if ok and contains and contains not in body:
        ok, error = False, f"response does not contain {contains!r}"
    elif not ok and not error:
        error = f"status {status}, expected {expect}"
    return {"time": datetime.now().isoformat(timespec="seconds"), "url": url, "status": status,
            "ms": ms if status else "", "ok": "yes" if ok else "no", "error": error}


def summarise(rows, slow_ms):
    """rows: list of dicts with the FIELDS. Return {url: stats dict} in first-seen order."""
    stats = {}
    for row in rows:
        item = stats.setdefault(row["url"], {"checks": 0, "ok": 0, "times": [], "slow": 0,
                                             "last_error": ""})
        item["checks"] += 1
        if row["ok"] == "yes":
            item["ok"] += 1
        elif row.get("error"):
            item["last_error"] = row["error"]
        if str(row.get("ms", "")).isdigit():
            item["times"].append(int(row["ms"]))
            item["slow"] += int(row["ms"]) > slow_ms
    for item in stats.values():
        item["state"] = ("DOWN" if item["ok"] == 0 else "DEGRADED" if item["ok"] < item["checks"]
                         else "SLOW" if item["slow"] else "UP")
    return stats


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if row.get("url")]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Poll health-check URLs and report failures.")
    parser.add_argument("urls", nargs="*", help="URLs to poll")
    parser.add_argument("--count", type=int, default=3, help="checks per URL (3)")
    parser.add_argument("--interval", type=float, default=2, help="seconds between rounds (2)")
    parser.add_argument("--timeout", type=float, default=5, help="seconds per request (5)")
    parser.add_argument("--expect", default="2xx", help="expected status: 200, 2xx, 204... (2xx)")
    parser.add_argument("--contains", help="text the response body must contain")
    parser.add_argument("--slow", type=int, default=1000, help="ms that count as slow (1000)")
    parser.add_argument("--csv", type=Path, help="append every check to this CSV log")
    parser.add_argument("--summarise", type=Path, help="summarise a CSV log instead of polling")
    args = parser.parse_args(argv)
    if not args.urls and not args.summarise:
        parser.error("give URLs to poll, or --summarise LOG.csv")
    if args.count < 1 or args.interval < 0:
        parser.error("--count must be at least 1 and --interval can't be negative")

    rows = []
    if args.summarise:
        if not args.summarise.is_file():
            parser.error(f"not a file: {args.summarise}")
        rows = read_csv(args.summarise)
    else:
        for round_number in range(args.count):
            if round_number:
                time.sleep(args.interval)
            for url in args.urls:
                result = check(url, args.timeout, args.expect, args.contains)
                rows.append(result)
                print(f"  {result['time'][11:]}  {'ok  ' if result['ok'] == 'yes' else 'FAIL'}  "
                      f"{result['status'] or '---':>3}  {str(result['ms']) + ' ms':>8}  {url}"
                      + (f"  ({result['error']})" if result["error"] else ""))
        if args.csv:
            fresh = not args.csv.exists()
            with args.csv.open("a", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                if fresh:
                    writer.writeheader()
                writer.writerows(rows)
    if not rows:
        print("No results.", file=sys.stderr)
        return 1
    print("\nSummary:")
    bad = 0
    for url, item in summarise(rows, args.slow).items():
        times = item["times"]
        speed = (f"avg {sum(times) // len(times)} ms, max {max(times)} ms" if times
                 else "no response")
        uptime = 100 * item["ok"] // item["checks"]
        problem = f"  last error: {item['last_error']}" if item["last_error"] else ""
        print(f"  {item['state']:<8} {url}  {item['ok']}/{item['checks']} ok ({uptime}%), "
              f"{speed}{problem}")
        bad += item["state"] != "UP"
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
