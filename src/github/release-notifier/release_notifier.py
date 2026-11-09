"""Check GitHub repositories for releases published since the last time you looked."""
import argparse
import json
import os
import re
import sys
import urllib.error  # web-ok: the network is only used when you name repositories
import urllib.request
from pathlib import Path

API = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
USER_AGENT = "daily-automation-scripts/1.0 (release notifier)"


def latest_release(repo, include_prereleases=False):
    """Return the newest release object for owner/repo, or None if it has none."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT,
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    path = f"/repos/{repo}/releases" + ("?per_page=5" if include_prereleases else "/latest")
    request = urllib.request.Request(f"{API}{path}", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read())
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return None  # no releases (or no such repository)
        raise
    if isinstance(data, list):
        data = next((r for r in data if not r.get("draft")), None)
    return data


def classify(repo, release, state, include_prereleases=False):
    """Return (status, tag): 'none', 'skipped', 'baseline', 'unchanged' or 'new'."""
    if not release:
        return "none", ""
    tag = release.get("tag_name", "")
    if release.get("prerelease") and not include_prereleases:
        return "skipped", tag
    if repo not in state:
        return "baseline", tag
    return ("unchanged" if state[repo] == tag else "new"), tag


def first_lines(body, count=3):
    lines = [line.strip(" -*#\t") for line in (body or "").splitlines() if line.strip()]
    return lines[:count]


def read_names(path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check repos for new releases.")
    parser.add_argument("repos", nargs="*", help="repositories as owner/name")
    parser.add_argument("--file", type=Path, help="text file with one owner/name per line")
    parser.add_argument("--state", type=Path, help="JSON file that remembers the last tag seen")
    parser.add_argument("--releases", type=Path,
                        help="read saved releases ({repo: release}) instead of asking GitHub")
    parser.add_argument("--include-prereleases", action="store_true")
    parser.add_argument("--report-all", action="store_true",
                        help="treat repos seen for the first time as new too")
    parser.add_argument("--no-update", action="store_true", help="don't change the state file")
    args = parser.parse_args(argv)

    try:
        names = args.repos + (read_names(args.file) if args.file else [])
        saved = json.loads(args.releases.read_text(encoding="utf-8")) if args.releases else None
        state = {}
        if args.state and args.state.is_file():
            state = json.loads(args.state.read_text(encoding="utf-8"))
        if not isinstance(state, dict) or (saved is not None and not isinstance(saved, dict)):
            raise ValueError("expected a JSON object")
    except (OSError, ValueError) as err:
        print(f"Couldn't read the input: {err}", file=sys.stderr)
        return 1
    if saved is not None:
        names = names or list(saved)
    bad = [n for n in names if not re.fullmatch(r"[\w.-]+/[\w.-]+", n)]
    if not names or bad:
        parser.error(f"not an owner/name repository: {bad[0]}" if bad
                     else "give repositories, --file FILE or --releases FILE")

    new, failed, updated = 0, 0, dict(state)
    for repo in names:
        try:
            release = (saved.get(repo) if saved is not None
                       else latest_release(repo, args.include_prereleases))
        except (urllib.error.URLError, OSError, ValueError) as err:
            print(f"?  {repo}: couldn't check ({getattr(err, 'reason', err)})")
            failed += 1
            continue
        status, tag = classify(repo, release, state, args.include_prereleases)
        if status == "baseline" and args.report_all:
            status = "new"
        label = {"none": "no releases yet", "skipped": f"{tag} is a pre-release, ignored",
                 "baseline": f"{tag} (first look, remembered)", "unchanged": f"{tag} (nothing new)",
                 "new": f"NEW {tag}"}[status]
        print(f"{'*' if status == 'new' else ' '}  {repo}: {label}")
        if status == "new":
            new += 1
            title = release.get("name") or tag
            print(f"     {title}, published {(release.get('published_at') or '')[:10]}")
            for line in first_lines(release.get("body")):
                print(f"       {line}")
            print(f"     {release.get('html_url', '')}")
        if status in ("new", "baseline", "unchanged"):
            updated[repo] = tag
    if args.state and not args.no_update and updated != state:
        args.state.write_text(json.dumps(updated, indent=1, sort_keys=True) + "\n",
                              encoding="utf-8")
    noun = "repository" if len(names) == 1 else "repositories"
    print(f"\n{new} new release(s) across {len(names)} {noun}.")
    return 1 if new or failed else 0


if __name__ == "__main__":
    sys.exit(main())
