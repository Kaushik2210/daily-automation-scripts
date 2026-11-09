"""Export the issues of a GitHub repository to CSV."""
import argparse
import csv
import io
import json
import os
import re
import sys
import urllib.error  # web-ok: the network is only used when you name a repository
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

API = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
USER_AGENT = "daily-automation-scripts/1.0 (issue exporter)"
COLUMNS = ["number", "title", "state", "author", "assignees", "labels", "comments", "created",
           "updated", "closed", "url"]


def api_get(path, params=None, max_pages=1):
    """GET a list from the GitHub API, following paging links (only to the same server)."""
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
        items += data if isinstance(data, list) else [data]
        nxt = re.search(r'<([^>]+)>;\s*rel="next"', link)
        if not nxt or not nxt.group(1).startswith(API):
            break
        url = nxt.group(1)
    return items


def to_row(issue):
    return {"number": issue.get("number"), "title": issue.get("title", ""),
            "state": issue.get("state", ""), "author": (issue.get("user") or {}).get("login", ""),
            "assignees": ";".join(a.get("login", "") for a in issue.get("assignees") or []),
            "labels": ";".join(label.get("name", "") for label in issue.get("labels") or []),
            "comments": issue.get("comments", 0), "created": (issue.get("created_at") or "")[:10],
            "updated": (issue.get("updated_at") or "")[:10],
            "closed": (issue.get("closed_at") or "")[:10], "url": issue.get("html_url", "")}


def filter_issues(issues, include_prs=False, state="all", labels=()):
    wanted = {label.casefold() for label in labels}
    for issue in issues:
        if "pull_request" in issue and not include_prs:
            continue
        if state != "all" and issue.get("state") != state:
            continue
        names = {label.get("name", "").casefold() for label in issue.get("labels") or []}
        if wanted and not wanted <= names:
            continue
        yield issue


def to_csv(issues):
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(to_row(issue) for issue in issues)
    return out.getvalue()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export a repository's issues to CSV.")
    parser.add_argument("repo", nargs="?", help="owner/repo, e.g. octocat/Hello-World")
    parser.add_argument("--from-file", type=Path, help="read a saved API response instead")
    parser.add_argument("--state", choices=["open", "closed", "all"], default="all")
    parser.add_argument("--label", action="append", default=[], help="only issues with this label")
    parser.add_argument("--include-prs", action="store_true", help="include pull requests too")
    parser.add_argument("--max-pages", type=int, default=10, help="pages of 100 issues (10)")
    parser.add_argument("--out", type=Path, help="write to this new CSV file instead of printing")
    args = parser.parse_args(argv)
    if not (args.repo or args.from_file):
        parser.error("give owner/repo or --from-file FILE")
    if args.repo and not re.fullmatch(r"[\w.-]+/[\w.-]+", args.repo):
        parser.error("repo must look like owner/name")
    if args.out and args.out.exists():
        print(f"{args.out} already exists - pick a new name so nothing is overwritten.")
        return 1

    try:
        if args.from_file:
            issues = json.loads(args.from_file.read_text(encoding="utf-8"))
        else:
            issues = api_get(f"/repos/{args.repo}/issues",
                             {"state": args.state, "per_page": 100}, max(args.max_pages, 1))
    except urllib.error.HTTPError as err:
        hint = {404: "repository not found (or private - set GITHUB_TOKEN)", 401: "bad token",
                403: "rate limit or access denied"}
        print(f"GitHub said {err.code}: {hint.get(err.code, err.reason)}.", file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"Couldn't get the issues: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1
    if not isinstance(issues, list):
        print("That file isn't a list of issues.", file=sys.stderr)
        return 1

    chosen = list(filter_issues(issues, args.include_prs, args.state, args.label))
    text = to_csv(chosen)
    if args.out:
        args.out.write_text(text, encoding="utf-8", newline="")
        print(f"Wrote {len(chosen)} issue(s) to {args.out}.")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
