"""List the open pull requests that are waiting for your review."""
import argparse
import json
import os
import sys
import urllib.error  # web-ok: the network is only used for a live lookup
import urllib.request
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode

API = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
USER_AGENT = "daily-automation-scripts/1.0 (pr review queue)"


def search_prs(user, org=None):
    """Ask GitHub's search for open PRs where a review from `user` was requested."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if user == "@me" and not token:
        raise ValueError("set GITHUB_TOKEN (or pass --user NAME) so GitHub knows who you are")
    query = f"is:pr is:open archived:false review-requested:{user}" + (f" org:{org}" if org else "")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT,
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{API}/search/issues?" + urlencode({"q": query, "per_page": 100, "sort": "created",
                                                "order": "asc"})
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as r:
        return json.loads(r.read())


def waiting_days(item, today):
    try:
        return (today - datetime.fromisoformat(item["created_at"]).date()).days
    except (KeyError, TypeError, ValueError):
        return 0


def queue(items, today, include_drafts=False):
    """Oldest-waiting first. Returns a list of plain dicts ready to print."""
    rows = []
    for item in items:
        if item.get("draft") and not include_drafts:
            continue
        repo = "/".join((item.get("repository_url") or "").rstrip("/").split("/")[-2:])
        author = (item.get("user") or {}).get("login", "?")
        rows.append({"repo": repo or "?", "number": item.get("number"),
                     "title": item.get("title", ""), "author": author,
                     "days": waiting_days(item, today), "comments": item.get("comments", 0),
                     "draft": bool(item.get("draft")), "url": item.get("html_url", "")})
    return sorted(rows, key=lambda r: (-r["days"], r["repo"], r["number"] or 0))


def main(argv=None):
    parser = argparse.ArgumentParser(description="List PRs waiting for your review.")
    parser.add_argument("--user", default="@me", help="whose review requests to list (@me)")
    parser.add_argument("--org", help="only repositories of this organisation or user")
    parser.add_argument("--include-drafts", action="store_true", help="show draft PRs too")
    parser.add_argument("--warn-days", type=int, default=7, help="flag PRs waiting this long (7)")
    parser.add_argument("--from-file", type=Path, help="read a saved search response instead")
    parser.add_argument("--today", help="treat this date as today, YYYY-MM-DD (for testing)")
    args = parser.parse_args(argv)
    try:
        today = date.fromisoformat(args.today) if args.today else date.today()
    except ValueError:
        parser.error("--today must look like 2026-11-09")

    try:
        data = (json.loads(args.from_file.read_text(encoding="utf-8")) if args.from_file
                else search_prs(args.user, args.org))
    except urllib.error.HTTPError as err:
        hint = {401: "bad token", 403: "rate limit or access denied", 422: "search was rejected"}
        print(f"GitHub said {err.code} ({hint.get(err.code, err.reason)}).", file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"Couldn't get the review queue: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        print("That doesn't look like a search response.", file=sys.stderr)
        return 1

    rows = queue(items, today, args.include_drafts)
    if not rows:
        print("Nothing is waiting for your review.")
        return 0
    print(f"{len(rows)} pull request(s) waiting for review:\n")
    for row in rows:
        flag = "  <-- waiting a while" if row["days"] >= args.warn_days else ""
        draft = " [draft]" if row["draft"] else ""
        print(f"{row['days']:>3}d  {row['repo']}#{row['number']}{draft}  {row['title']}{flag}")
        print(f"      by {row['author']}, {row['comments']} comment(s)  {row['url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
