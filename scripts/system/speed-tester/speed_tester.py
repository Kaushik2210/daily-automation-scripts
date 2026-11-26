"""Measure download speed by fetching a test file, or summarise saved timings."""
import argparse
import csv
import statistics
import sys
import time
import urllib.error  # web-ok: the network is only used for live runs
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_URL = "https://speed.cloudflare.com/__down?bytes=25000000"
CHUNK = 64 * 1024
USER_AGENT = "daily-automation-scripts/1.0 (speed tester)"


def mbps(size, seconds):
    """Megabits per second (decimal, like internet providers quote)."""
    return size * 8 / 1_000_000 / seconds if seconds > 0 else 0.0


def megabytes(size):
    return size / 1_000_000


def download(url, max_bytes, max_seconds, timeout, clock=time.perf_counter):
    """Fetch `url` once and return {bytes, seconds, first_byte, mbps}. Stops early at the limits."""
    started = clock()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    total, first = 0, None
    with urllib.request.urlopen(request, timeout=timeout) as response:
        while True:
            chunk = response.read(CHUNK)
            if not chunk:
                break
            if first is None:
                first = clock() - started
            total += len(chunk)
            if (max_bytes and total >= max_bytes) or clock() - started >= max_seconds:
                break
    seconds = clock() - started
    return {"bytes": total, "seconds": seconds, "first_byte": first or seconds,
            "mbps": mbps(total, seconds)}


def parse_saved(text):
    """Lines of `bytes seconds` (comments with # allowed) -> run dicts."""
    runs = []
    for number, line in enumerate(text.splitlines(), 1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        try:
            size, seconds = line.replace(",", " ").split()[:2]
            run = {"bytes": int(size), "seconds": float(seconds), "first_byte": None}
        except ValueError:
            raise ValueError(f"line {number}: expected 'bytes seconds', got '{line}'") from None
        if run["bytes"] <= 0 or run["seconds"] <= 0:
            raise ValueError(f"line {number}: bytes and seconds must be above 0")
        run["mbps"] = mbps(run["bytes"], run["seconds"])
        runs.append(run)
    return runs


def summarise(runs):
    speeds = [r["mbps"] for r in runs]
    return {"runs": len(runs), "average": statistics.fmean(speeds),
            "median": statistics.median(speeds), "best": max(speeds), "worst": min(speeds)}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Measure download speed.")
    parser.add_argument("--url", default=DEFAULT_URL, help="file to download (a 25 MB test file)")
    parser.add_argument("--runs", type=int, default=3, help="how many times to download (3)")
    parser.add_argument("--max-bytes", type=int, default=0,
                        help="stop each run after this many bytes")
    parser.add_argument("--max-seconds", type=float, default=30.0,
                        help="stop each run after this many seconds (30)")
    parser.add_argument("--timeout", type=float, default=15.0,
                        help="connection timeout in seconds (15)")
    parser.add_argument("--min-mbps", type=float, help="exit 1 if the average is below this")
    parser.add_argument("--log", type=Path, help="append each run to this CSV file")
    parser.add_argument("--from-file", type=Path, dest="source",
                        help="summarise saved 'bytes seconds' lines instead of downloading")
    args = parser.parse_args(argv)
    if args.runs < 1 or args.max_bytes < 0 or args.max_seconds <= 0 or args.timeout <= 0:
        parser.error("--runs must be at least 1 and the limits must be positive")
    if urlparse(args.url).scheme not in ("http", "https"):
        parser.error("--url must start with http:// or https://")

    runs = []
    try:
        if args.source:
            runs = parse_saved(args.source.read_text(encoding="utf-8"))
        else:
            print(f"Downloading {args.url}\n")
            for _ in range(args.runs):
                runs.append(download(args.url, args.max_bytes, args.max_seconds, args.timeout))
                print(f"  run {len(runs)}: {megabytes(runs[-1]['bytes']):.1f} MB in "
                      f"{runs[-1]['seconds']:.2f} s")
    except (OSError, ValueError, urllib.error.URLError) as err:
        print(f"Speed test failed: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1
    if not runs:
        print("No timings to report.", file=sys.stderr)
        return 1

    for number, run in enumerate(runs, 1):
        lead = f"{number:>3}. {megabytes(run['bytes']):>6.1f} MB in {run['seconds']:>5.2f} s = "
        delay = f"  (first byte {run['first_byte'] * 1000:.0f} ms)" if run["first_byte"] else ""
        per_second = megabytes(run["bytes"]) / run["seconds"]
        print(f"{lead}{run['mbps']:>7.1f} Mbit/s  {per_second:>5.1f} MB/s{delay}")
    s = summarise(runs)
    print(f"\n{s['runs']} run(s): average {s['average']:.1f} Mbit/s, median {s['median']:.1f}, "
          f"best {s['best']:.1f}, worst {s['worst']:.1f}")
    if args.log and not args.source:
        fresh = not args.log.exists() or args.log.stat().st_size == 0
        with args.log.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            if fresh:
                writer.writerow(["time", "url", "bytes", "seconds", "mbps"])
            for run in runs:
                writer.writerow([datetime.now().isoformat(timespec="seconds"), args.url,
                                 run["bytes"], f"{run['seconds']:.3f}", f"{run['mbps']:.2f}"])
        print(f"Appended {len(runs)} row(s) to {args.log}")
    if args.min_mbps is not None and s["average"] < args.min_mbps:
        print(f"Average {s['average']:.1f} is below the {args.min_mbps:g} Mbit/s minimum.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
