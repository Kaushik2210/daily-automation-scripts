"""Report stars, forks and recent activity for a GitHub user or repository."""
import argparse
import json
import os
import re
import sys
import urllib.error  # web-ok: the network is only used when you name a user or repository
import urllib.request
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode

API = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
USER_AGENT = "daily-automation-scripts/1.0 (github stats reporter)"


def api_get(path, params=None, max_pages=1):
    """GET from the GitHub API (public data works without a token), following paging links."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT,
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{API}{path}" + (f"?{urlencode(params)}" if params else "")
    items = []
    for _ in range(max_pages):
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as r:
            data, link = json.loads(r.read()), r.headers.get("Link", "")
        if not isinstance(data, list):
            return data
        items += data
        nxt = re.search(r'<([^>]+)>;\s*rel="next"', link)
        if not nxt or not nxt.group(1).startswith(API):  # never send the token elsewhere
            break
        url = nxt.group(1)
    return items


def days_since(stamp, today):
    try:
        return (today - datetime.fromisoformat(stamp).date()).days
    except (TypeError, ValueError):
        return None


def ago(days):
    if days is None:
        return "unknown"
    if days < 1:
        return "today"
    return f"{days} day(s) ago" if days < 60 else f"{days // 30} month(s) ago"


def repo_report(repo, today):
    license_id = (repo.get("license") or {}).get("spdx_id") or "none"
    lines = [f"{repo.get('full_name', repo.get('name'))}"
             + ("  [archived]" if repo.get("archived") else "")
             + ("  [fork]" if repo.get("fork") else ""),
             f"  {repo.get('description') or '(no description)'}",
             f"  Language : {repo.get('language') or 'n/a'}    License: {license_id}",
             f"  Stars    : {repo.get('stargazers_count', 0):,}    "
             f"Forks: {repo.get('forks_count', 0):,}    "
             f"Open issues: {repo.get('open_issues_count', 0):,}",
             f"  Last push: {ago(days_since(repo.get('pushed_at'), today))}"]
    return "\n".join(lines)


def user_report(repos, today, include_forks=False, top=5):
    counted = [r for r in repos if include_forks or not r.get("fork")]
    stars = sum(r.get("stargazers_count", 0) for r in counted)
    forks = sum(r.get("forks_count", 0) for r in counted)
    active = sum(1 for r in counted
                 if (days_since(r.get("pushed_at"), today) or 9999) <= 30)
    languages = Counter(r["language"] for r in counted if r.get("language"))
    lines = [f"{len(counted)} repositories"
             + ("" if include_forks else f" (+{len(repos) - len(counted)} forks left out)"),
             f"  Stars: {stars:,}    Forks: {forks:,}    Pushed in the last 30 days: {active}",
             "  Languages: " + (", ".join(f"{n} ({c})" for n, c in languages.most_common(4))
                                or "n/a"), "", f"Top {min(top, len(counted))} by stars:"]
    for repo in sorted(counted, key=lambda r: -r.get("stargazers_count", 0))[:top]:
        lines.append(f"  {repo.get('stargazers_count', 0):>6,} *  {repo['name']:<20} "
                     f"{repo.get('language') or '':<12} pushed "
                     f"{ago(days_since(repo.get('pushed_at'), today))}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Report stars, forks and activity on GitHub.")
    parser.add_argument("target", nargs="?", help="a user name (octocat) or owner/repo")
    parser.add_argument("--from-file", type=Path, help="read a saved API response instead")
    parser.add_argument("--include-forks", action="store_true", help="count forked repos too")
    parser.add_argument("--today", help="treat this date as today, YYYY-MM-DD (for testing)")
    args = parser.parse_args(argv)
    if not (args.target or args.from_file):
        parser.error("give a user or owner/repo, or --from-file FILE")
    try:
        today = date.fromisoformat(args.today) if args.today else date.today()
    except ValueError:
        parser.error("--today must look like 2026-11-09")

    try:
        if args.from_file:
            data = json.loads(args.from_file.read_text(encoding="utf-8"))
        elif "/" in args.target:
            data = api_get(f"/repos/{args.target}")
        else:
            data = api_get(f"/users/{args.target}/repos",
                           {"per_page": 100, "sort": "pushed"}, max_pages=5)
    except urllib.error.HTTPError as err:
        hint = {404: "not found", 401: "bad token", 403: "rate limit or access denied"}
        print(f"GitHub said {err.code} ({hint.get(err.code, err.reason)}).", file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"Couldn't get the data: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1

    if isinstance(data, dict):
        print(repo_report(data, today))
    elif isinstance(data, list) and data:
        print(user_report(data, today, args.include_forks))
    else:
        print("No repositories found.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
