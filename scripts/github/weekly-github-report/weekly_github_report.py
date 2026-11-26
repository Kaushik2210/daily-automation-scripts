"""Write a weekly activity report (commits, pull requests, issues) across your GitHub repos."""
import argparse
import json
import os
import re
import sys
import urllib.error  # web-ok: the network is only used for live repositories
import urllib.request
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

API = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
USER_AGENT = "daily-automation-scripts/1.0 (weekly report)"


def when(text):
    return datetime.fromisoformat(text) if text else None


def window(week_ending, days):
    """(since, until): `days` days ending at the end of the `week_ending` date, UTC."""
    until = datetime.combine(week_ending + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    return until - timedelta(days=days), until


def api_get(path, params, token):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url, items = f"{API}{path}?{urlencode({**params, 'per_page': 100})}", []
    for _ in range(10):  # at most 1000 items per list
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers),
                                    timeout=20) as response:
            items += json.loads(response.read())
            link = re.search(r'<([^>]+)>;\s*rel="next"', response.headers.get("Link", ""))
        if not link or not link.group(1).startswith(API):  # never send the token elsewhere
            break
        url = link.group(1)
    return items


def fetch_repo(full_name, since, token):
    """Pull one repository's recent activity and reshape it like the saved format."""
    stamp = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    commits = api_get(f"/repos/{full_name}/commits", {"since": stamp}, token)
    pulls = api_get(f"/repos/{full_name}/pulls",
                    {"state": "all", "sort": "updated", "direction": "desc"}, token)
    issues = api_get(f"/repos/{full_name}/issues", {"state": "all", "since": stamp}, token)
    def login(commit):
        return (commit.get("author") or {}).get("login") or commit["commit"]["author"]["name"]

    return {
        "commits": [{"sha": c["sha"][:7], "date": c["commit"]["author"]["date"],
                     "author": login(c),
                     "message": c["commit"]["message"].splitlines()[0]} for c in commits],
        "pulls": [{"number": p["number"], "title": p["title"], "user": p["user"]["login"],
                   "created_at": p["created_at"], "merged_at": p.get("merged_at"),
                   "closed_at": p.get("closed_at")} for p in pulls],
        "issues": [{"number": i["number"], "title": i["title"], "user": i["user"]["login"],
                    "labels": [label["name"] for label in i.get("labels", [])],
                    "created_at": i["created_at"], "closed_at": i.get("closed_at")}
                   for i in issues if "pull_request" not in i]}


def inside(text, since, until):
    moment = when(text)
    return bool(moment and since <= moment < until)


def summarise(bundle, since, until):
    """Per-repo numbers for the window: {repo: {commits, authors, opened, merged, ...}}."""
    report = {}
    for repo, data in bundle["repos"].items():
        commits = [c for c in data.get("commits", []) if inside(c["date"], since, until)]
        pulls, issues = data.get("pulls", []), data.get("issues", [])
        report[repo] = {
            "commits": commits,
            "authors": Counter(c["author"] for c in commits),
            "prs_opened": [p for p in pulls if inside(p["created_at"], since, until)],
            "prs_merged": [p for p in pulls if inside(p.get("merged_at"), since, until)],
            "prs_open": [p for p in pulls if not p.get("merged_at") and not p.get("closed_at")],
            "issues_opened": [i for i in issues if inside(i["created_at"], since, until)],
            "issues_closed": [i for i in issues if inside(i.get("closed_at"), since, until)]}
    return report


def render(report, since, until):
    last_day = (until - timedelta(days=1)).date()
    lines = [f"# Weekly GitHub report: {since.date()} to {last_day}", ""]
    total = {key: sum(len(r[key]) for r in report.values())
             for key in ("commits", "prs_opened", "prs_merged", "issues_opened", "issues_closed")}
    lines += ["| Repository | Commits | PRs opened | PRs merged | Issues opened | Issues closed |",
              "|---|---|---|---|---|---|"]
    for repo, r in report.items():
        lines.append(f"| {repo} | {len(r['commits'])} | {len(r['prs_opened'])} | "
                     f"{len(r['prs_merged'])} | {len(r['issues_opened'])} | "
                     f"{len(r['issues_closed'])} |")
    lines.append(f"| **Total** | {total['commits']} | {total['prs_opened']} | "
                 f"{total['prs_merged']} | {total['issues_opened']} | {total['issues_closed']} |")
    people = sum((r["authors"] for r in report.values()), Counter())
    if people:
        lines += ["", "## Top contributors", ""]
        lines += [f"- {name}: {count} commit(s)" for name, count in people.most_common(5)]
    merged = [(repo, p) for repo, r in report.items() for p in r["prs_merged"]]
    if merged:
        lines += ["", "## Merged this week", ""]
        lines += [f"- {repo}#{p['number']} {p['title']} (@{p['user']})" for repo, p in merged]
    closed = [(repo, i) for repo, r in report.items() for i in r["issues_closed"]]
    if closed:
        lines += ["", "## Issues closed", ""]
        lines += [f"- {repo}#{i['number']} {i['title']}" for repo, i in closed]
    waiting = [(repo, p) for repo, r in report.items() for p in r["prs_open"]]
    if waiting:
        lines += ["", "## Still open", ""]
        lines += [f"- {repo}#{p['number']} {p['title']} (@{p['user']}, opened "
                  f"{when(p['created_at']).date()})" for repo, p in waiting]
    return "\n".join(lines) + "\n", total


def main(argv=None):
    parser = argparse.ArgumentParser(description="Weekly activity report across GitHub repos.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--repos", nargs="+", metavar="OWNER/NAME", help="repositories to report")
    source.add_argument("--from-json", type=Path, dest="saved",
                        help="saved activity (see the README) instead of calling GitHub")
    parser.add_argument("--week-ending", help="last day, YYYY-MM-DD (today)")
    parser.add_argument("--days", type=int, default=7, help="length of the report in days (7)")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", type=Path, help="write to this new file instead of printing")
    args = parser.parse_args(argv)
    if not 1 <= args.days <= 90:
        parser.error("--days must be between 1 and 90")
    try:
        ending = date.fromisoformat(args.week_ending) if args.week_ending else date.today()
    except ValueError:
        parser.error(f"--week-ending must look like 2026-11-22, got '{args.week_ending}'")
    if args.output and args.output.exists():
        print(f"{args.output} already exists; pick a new name.", file=sys.stderr)
        return 1
    try:
        if args.saved:
            bundle = json.loads(args.saved.read_text(encoding="utf-8"))
            if args.week_ending:
                since, until = window(ending, args.days)
            else:
                since, until = when(bundle["since"]), when(bundle["until"])
        else:
            since, until = window(ending, args.days)
            token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
            bundle = {"repos": {r: fetch_repo(r, since, token) for r in args.repos}}
        report = summarise(bundle, since, until)
    except (OSError, ValueError, KeyError, TypeError, urllib.error.URLError) as err:
        print(f"Can't build the report: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1

    text, total = render(report, since, until)
    if args.format == "json":
        text = json.dumps({"since": since.isoformat(), "until": until.isoformat(), "totals": total,
                           "repos": {repo: {k: (len(v) if isinstance(v, list) else dict(v))
                                            for k, v in r.items()}
                                     for repo, r in report.items()}}, indent=1) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote {args.output} ({total['commits']} commits across {len(report)} repos).")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
