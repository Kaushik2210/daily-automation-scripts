"""Show how much of your GitHub API rate limit is left and when it resets."""
import argparse
import json
import os
import sys
import time
import urllib.error  # web-ok: the network is only used for a live check
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

API = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
USER_AGENT = "daily-automation-scripts/1.0 (rate limit checker)"


def fetch_limits():
    """Ask GitHub for the current limits (this request itself doesn't use up any quota)."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT,
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{API}/rate_limit", headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read()), bool(token)


def describe_wait(seconds):
    if seconds <= 0:
        return "already reset"
    minutes, secs = divmod(int(seconds), 60)
    if minutes >= 60:
        return f"in {minutes // 60}h {minutes % 60:02d}m"
    return f"in {minutes}m {secs:02d}s" if minutes else f"in {secs}s"


def summarize(data, now):
    """Return [(name, used, limit, remaining, percent left, reset time, wait text)]."""
    rows = []
    for name, info in sorted((data.get("resources") or {}).items()):
        limit, remaining = info.get("limit", 0), info.get("remaining", 0)
        if not limit:
            continue
        reset = datetime.fromtimestamp(info.get("reset", 0), tz=UTC)
        rows.append((name, info.get("used", limit - remaining), limit, remaining,
                     100 * remaining / limit, reset, describe_wait(info.get("reset", 0) - now)))
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description="Show your GitHub API rate limit status.")
    parser.add_argument("--from-file", type=Path, help="read a saved /rate_limit response")
    parser.add_argument("--warn-below", type=float, default=10.0,
                        help="exit 1 when any limit has less than this percent left (10)")
    parser.add_argument("--now", help="treat this UTC time as now, e.g. 2026-11-09T11:30 (testing)")
    args = parser.parse_args(argv)
    try:
        now = (datetime.fromisoformat(args.now).replace(tzinfo=UTC).timestamp()
               if args.now else time.time())
    except ValueError:
        parser.error("--now must look like 2026-11-09T11:30")

    signed_in = None
    try:
        if args.from_file:
            data = json.loads(args.from_file.read_text(encoding="utf-8"))
        else:
            data, signed_in = fetch_limits()
    except urllib.error.HTTPError as err:
        print(f"GitHub said {err.code} ({'bad token' if err.code == 401 else err.reason}).",
              file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"Couldn't read the rate limit: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1

    rows = summarize(data if isinstance(data, dict) else {}, now)
    if not rows:
        print("No rate limit information found.", file=sys.stderr)
        return 1
    if signed_in is not None:
        print("Using a token." if signed_in else "No token set (anonymous, lower limits).")
    low = 0
    for name, used, limit, remaining, percent, reset, wait in rows:
        warn = percent < args.warn_below
        low += warn
        print(f"{name:<10} {remaining:>6,} of {limit:<6,} left ({percent:>5.1f}%)  "
              f"used {used:,}  resets {reset:%H:%M} UTC {wait}" + ("  <-- LOW" if warn else ""))
    return 1 if low else 0


if __name__ == "__main__":
    sys.exit(main())
