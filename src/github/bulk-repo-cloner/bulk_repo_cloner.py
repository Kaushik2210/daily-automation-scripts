"""Clone many repositories from a list file, a GitHub user or organisation, or saved API output."""
import argparse
import fnmatch
import json
import os
import re
import subprocess  # web-ok: git only runs with --apply; the plan works offline
import sys
import urllib.error  # web-ok: the network is only used for --user/--org
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlencode

API = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
USER_AGENT = "daily-automation-scripts/1.0 (bulk repo cloner)"


def repo_from_api(item, ssh):
    """Turn one GitHub API repository object into {name, url, language, fork, archived}."""
    url = item.get("ssh_url") if ssh else item.get("clone_url")
    if not url:
        base = item.get("html_url") or f"https://github.com/{item.get('full_name', '')}"
        url = (f"git@github.com:{item['full_name']}.git" if ssh and item.get("full_name")
               else base + ".git")
    return {"name": item["name"], "url": url, "language": item.get("language") or "",
            "fork": bool(item.get("fork")), "archived": bool(item.get("archived"))}


def repo_from_line(line):
    """'owner/repo', a git URL, or 'URL optional-folder-name' -> {name, url}."""
    parts = line.split()
    target = parts[0]
    if re.fullmatch(r"[\w.-]+/[\w.-]+", target):
        target = f"https://github.com/{target}.git"
    name = parts[1] if len(parts) > 1 else re.sub(r"\.git$", "", re.split(r"[/:\\]", target)[-1])
    return {"name": name, "url": target, "language": "", "fork": False, "archived": False}


def read_list(path):
    repos = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            repos.append(repo_from_line(line))
    return repos


def api_repos(kind, name, limit):
    """List a user's or organisation's repositories through the GitHub API (paged)."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{API}/{kind}s/{name}/repos?" + urlencode({"per_page": 100, "type": "owner"
                                                        if kind == "user" else "all"})
    items = []
    while url and (not limit or len(items) < limit):
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers),
                                    timeout=20) as response:
            items += json.loads(response.read())
            link = re.search(r'<([^>]+)>;\s*rel="next"', response.headers.get("Link", ""))
        # only follow links on the API host, so the token never leaves it
        url = link.group(1) if link and link.group(1).startswith(API) else None
    return items


def select(repos, include_forks, include_archived, language, pattern, limit):
    chosen = []
    for repo in repos:
        if (repo["fork"] and not include_forks) or (repo["archived"] and not include_archived):
            continue
        if language and repo["language"].lower() != language.lower():
            continue
        if pattern and not fnmatch.fnmatch(repo["name"], pattern):
            continue
        chosen.append(repo)
    return chosen[:limit] if limit else chosen


def clone_one(repo, dest, depth):
    target = dest / repo["name"]
    command = ["git", "clone", "--quiet", *(["--depth", str(depth)] if depth else []),
               repo["url"], str(target)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=1800, check=False)
    if result.returncode:
        raise OSError((result.stderr.strip().splitlines() or ["git clone failed"])[-1])
    return target


def pull_one(target):
    result = subprocess.run(["git", "-C", str(target), "pull", "--ff-only", "--quiet"],
                            capture_output=True, text=True, timeout=600, check=False)
    if result.returncode:
        raise OSError((result.stderr.strip().splitlines() or ["git pull failed"])[-1])


def main(argv=None):
    parser = argparse.ArgumentParser(description="Clone many repositories at once.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--list", type=Path, help="text file: owner/repo or git URL per line")
    source.add_argument("--user", help="clone this GitHub user's repositories")
    source.add_argument("--org", help="clone this GitHub organisation's repositories")
    source.add_argument("--from-json", type=Path, dest="saved",
                        help="saved GitHub API output (a JSON list of repositories)")
    parser.add_argument("--dest", type=Path, default=Path("repos"), help="parent folder (repos)")
    parser.add_argument("--ssh", action="store_true", help="use SSH URLs for API repositories")
    parser.add_argument("--include-forks", action="store_true")
    parser.add_argument("--include-archived", action="store_true")
    parser.add_argument("--language", help="only repositories in this language")
    parser.add_argument("--pattern", help="only names matching this, e.g. 'api-*'")
    parser.add_argument("--limit", type=int, default=0, help="at most N repositories")
    parser.add_argument("--depth", type=int, default=0, help="shallow clone with N commits")
    parser.add_argument("--jobs", type=int, default=4, help="clones at once (4)")
    parser.add_argument("--update", action="store_true", help="pull repositories already cloned")
    parser.add_argument("--apply", action="store_true",
                        help="really clone (default only shows the plan)")
    args = parser.parse_args(argv)
    if args.jobs < 1 or args.limit < 0 or args.depth < 0:
        parser.error("--jobs must be at least 1; --limit and --depth can't be negative")

    try:
        if args.list:
            repos = read_list(args.list)
        elif args.saved:
            data = json.loads(args.saved.read_text(encoding="utf-8"))
            repos = [repo_from_api(item, args.ssh) for item in data]
        else:
            kind, name = ("user", args.user) if args.user else ("org", args.org)
            repos = [repo_from_api(item, args.ssh) for item in api_repos(kind, name, args.limit)]
    except (OSError, ValueError, KeyError, urllib.error.URLError) as err:
        print(f"Can't get the repository list: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1
    repos = select(repos, args.include_forks, args.include_archived, args.language, args.pattern,
                   args.limit)
    if not repos:
        print("No repositories match.", file=sys.stderr)
        return 1

    todo = []
    print(f"{len(repos)} repositor{'y' if len(repos) == 1 else 'ies'} -> {args.dest}/")
    for repo in repos:
        target = args.dest / repo["name"]
        if target.exists():
            state = "exists, will pull" if args.update else "exists, skipped"
            if args.update and (target / ".git").exists():
                todo.append(("pull", repo))
        else:
            state = "will clone"
            todo.append(("clone", repo))
        info = f" [{repo['language']}]" if repo["language"] else ""
        print(f"  {repo['name']:<24} {state:<17} {repo['url']}{info}")
    if not args.apply:
        print(f"\nDry run: {len(todo)} action(s). Use --apply to start ({args.jobs} at once).")
        return 0
    args.dest.mkdir(parents=True, exist_ok=True)
    failures = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        jobs = {}
        for action, repo in todo:
            if action == "clone":
                jobs[pool.submit(clone_one, repo, args.dest, args.depth)] = (action, repo)
            else:
                jobs[pool.submit(pull_one, args.dest / repo["name"])] = (action, repo)
        for job in as_completed(jobs):
            action, repo = jobs[job]
            try:
                job.result()
                print(f"done  {action:<5} {repo['name']}")
            except (OSError, subprocess.SubprocessError) as err:
                failures += 1
                print(f"FAIL  {action:<5} {repo['name']}: {err}")
    print(f"\n{len(todo) - failures} succeeded, {failures} failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
