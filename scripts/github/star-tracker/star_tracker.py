"""Log the star counts of a user's repositories over time and show what changed."""
import argparse
import csv
import json
import os
import re
import sys
import urllib.error  # web-ok: the network is only used when you name a user
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

API = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
USER_AGENT = "daily-automation-scripts/1.0 (star tracker)"
HEADER = ["date", "repo", "stars", "forks"]


def fetch_repos(user, max_pages=5):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT,
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{API}/users/{user}/repos?" + urlencode({"per_page": 100, "type": "owner"})
    repos = []
    for _ in range(max_pages):
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as r:
            repos += json.loads(r.read())
            link = r.headers.get("Link", "")
        nxt = re.search(r'<([^>]+)>;\s*rel="next"', link)
        if not nxt or not nxt.group(1).startswith(API):
            break
        url = nxt.group(1)
    return repos


def read_log(path):
    """Return {repo: [(date, stars, forks), ...]} sorted by date."""
    history = {}
    if path and path.is_file():
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                try:
                    history.setdefault(row["repo"], []).append(
                        (row["date"], int(row["stars"]), int(row.get("forks") or 0)))
                except (KeyError, ValueError):
                    continue
    return {repo: sorted(rows) for repo, rows in history.items()}


def snapshot(repos, include_forks=False):
    return {r["full_name"]: (r.get("stargazers_count", 0), r.get("forks_count", 0))
            for r in repos if r.get("full_name") and (include_forks or not r.get("fork"))}


def compare(current, history, today):
    """Rows of (repo, stars, change, since-date); change is None for a first sighting."""
    rows = []
    for repo, (stars, _forks) in current.items():
        earlier = [entry for entry in history.get(repo, []) if entry[0] < today]
        rows.append((repo, stars, stars - earlier[-1][1] if earlier else None,
                     earlier[-1][0] if earlier else None))
    return sorted(rows, key=lambda r: (-r[1], r[0]))


def record(path, current, history, today):
    """Append today's counts (once per repo per day). Returns how many rows were added."""
    new_rows = [[today, repo, stars, forks] for repo, (stars, forks) in sorted(current.items())
                if not any(entry[0] == today for entry in history.get(repo, []))]
    if new_rows:
        fresh = not path.exists() or path.stat().st_size == 0
        with path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            if fresh:
                writer.writerow(HEADER)
            writer.writerows(new_rows)
    return len(new_rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Track repository stars over time.")
    parser.add_argument("user", nargs="?", help="GitHub user name")
    parser.add_argument("--from-file", type=Path, help="read a saved repos response instead")
    parser.add_argument("--log", type=Path, help="CSV file that keeps the history")
    parser.add_argument("--no-record", action="store_true", help="compare only, don't add rows")
    parser.add_argument("--include-forks", action="store_true", help="track forked repos too")
    parser.add_argument("--today", help="treat this date as today, YYYY-MM-DD (for testing)")
    args = parser.parse_args(argv)
    if not (args.user or args.from_file):
        parser.error("give a user name or --from-file FILE")
    try:
        today = (date.fromisoformat(args.today) if args.today else date.today()).isoformat()
    except ValueError:
        parser.error("--today must look like 2026-11-09")

    try:
        repos = (json.loads(args.from_file.read_text(encoding="utf-8")) if args.from_file
                 else fetch_repos(args.user))
    except urllib.error.HTTPError as err:
        print(f"GitHub said {err.code} ({'user not found' if err.code == 404 else err.reason}).",
              file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"Couldn't get the repositories: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1
    if not isinstance(repos, list):
        print("That isn't a list of repositories.", file=sys.stderr)
        return 1

    current = snapshot(repos, args.include_forks)
    if not current:
        print("No repositories to track.")
        return 1
    history = read_log(args.log)
    rows = compare(current, history, today)
    width = max(len(repo) for repo, *_ in rows)
    for repo, stars, change, since in rows:
        note = "first reading" if change is None else f"{change:+d} since {since}"
        print(f"{repo:<{width}}  {stars:>7,}  {note}")
    total = sum(stars for _, stars, _, _ in rows)
    gained = sum(change for _, _, change, _ in rows if change)
    print(f"{'Total':<{width}}  {total:>7,}  {gained:+d} across repos with history")
    if args.log and not args.no_record:
        print(f"Saved {record(args.log, current, history, today)} row(s) to {args.log}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
