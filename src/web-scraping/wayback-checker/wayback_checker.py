"""Look up Wayback Machine snapshots for URLs, or read saved lookup responses."""
import argparse
import json
import sys
import time
import urllib.error  # web-ok: the network is only used when you look up URLs yourself
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

API = "https://archive.org/wayback/available"
USER_AGENT = "daily-automation-scripts/1.0 (wayback checker)"


def parse_snapshot(response):
    """Return (when, link) for the closest snapshot in an availability response, or None."""
    closest = (response.get("archived_snapshots") or {}).get("closest") or {}
    if not closest.get("available") or not closest.get("url"):
        return None
    try:
        when = datetime.strptime(str(closest["timestamp"]), "%Y%m%d%H%M%S")
    except (KeyError, ValueError):
        return None
    link = closest["url"].replace("http://web.archive.org", "https://web.archive.org", 1)
    return when, link


def lookup(url, timestamp=None, timeout=20):
    query = {"url": url, **({"timestamp": timestamp} if timestamp else {})}
    request = urllib.request.Request(f"{API}?{urlencode(query)}",
                                     headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read(1024 * 1024).decode("utf-8"))
    data.setdefault("url", url)
    return data


def describe(url, snapshot):
    if not snapshot:
        return f"{url}: no snapshot saved"
    when, link = snapshot
    return f"{url}: {when:%Y-%m-%d %H:%M} UTC  {link}"


def read_urls(path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]


def check_timestamp(text):
    if not text.isdigit() or len(text) not in (4, 6, 8, 10, 12, 14):
        raise argparse.ArgumentTypeError("use YYYY, YYYYMM, YYYYMMDD ... up to YYYYMMDDhhmmss")
    return text


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find Wayback Machine snapshots for URLs.")
    parser.add_argument("urls", nargs="*", help="addresses to look up")
    parser.add_argument("--file", type=Path, help="text file with one URL per line")
    parser.add_argument("--timestamp", type=check_timestamp,
                        help="find the snapshot closest to this date (YYYYMMDD)")
    parser.add_argument("--response", type=Path,
                        help="read saved availability responses (JSON) instead of asking")
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between lookups (1)")
    args = parser.parse_args(argv)

    results = []
    try:
        if args.response:
            data = json.loads(args.response.read_text(encoding="utf-8"))
            for number, item in enumerate(data if isinstance(data, list) else [data], 1):
                results.append((item.get("url") or f"response {number}", parse_snapshot(item)))
        else:
            urls = args.urls + (read_urls(args.file) if args.file else [])
            if not urls:
                parser.error("give URLs, --file FILE or --response FILE")
            for number, url in enumerate(urls):
                if number and args.delay > 0:
                    time.sleep(args.delay)
                results.append((url, parse_snapshot(lookup(url, args.timestamp))))
    except (urllib.error.URLError, OSError, ValueError, AttributeError) as err:
        print(f"Couldn't complete the lookup: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1
    for url, snapshot in results:
        print(describe(url, snapshot))
    missing = sum(snapshot is None for _, snapshot in results)
    print(f"{len(results) - missing} of {len(results)} URL(s) have a snapshot.")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
