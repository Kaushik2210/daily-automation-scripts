"""Show which languages your GitHub repositories are written in."""
import argparse
import json
import os
import re
import sys
import urllib.error  # web-ok: the network is only used when you name a user
import urllib.request
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode

API = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
USER_AGENT = "daily-automation-scripts/1.0 (language breakdown)"


def api_get(path, params=None, max_pages=1):
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
        if not nxt or not nxt.group(1).startswith(API):
            break
        url = nxt.group(1)
    return items


def tally(repos, weight="count", include_forks=False, include_archived=True):
    """Return a Counter of language -> weight (repo count, stars or size in KB)."""
    totals = Counter()
    for repo in repos:
        if (repo.get("fork") and not include_forks) or (repo.get("archived")
                                                          and not include_archived):
            continue
        language = repo.get("language")
        if not language:
            continue
        amount = {"count": 1, "stars": repo.get("stargazers_count", 0),
                  "size": repo.get("size", 0)}[weight]
        totals[language] += amount
    return Counter({k: v for k, v in totals.items() if v > 0})


def bytes_by_language(repos, limit):
    """Sum real per-language byte counts from the API (one request per repository)."""
    totals = Counter()
    for repo in repos[:limit]:
        if repo.get("full_name") and not repo.get("fork"):
            totals.update(api_get(f"/repos/{repo['full_name']}/languages"))
    return totals


def render(totals, unit, width=30):
    grand = sum(totals.values())
    lines = []
    for language, amount in totals.most_common():
        share = amount / grand
        bar = "#" * max(1, round(share * width))
        lines.append(f"{language:<14} {share:>6.1%}  {bar:<{width}} {amount:,} {unit}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Language share across your repositories.")
    parser.add_argument("user", nargs="?", help="GitHub user name")
    parser.add_argument("--from-file", type=Path, help="read a saved repos response instead")
    parser.add_argument("--weight", choices=["count", "stars", "size"], default="count",
                        help="count repos (default), or weight by stars or repository size")
    parser.add_argument("--bytes", action="store_true",
                        help="use real code bytes per language (online, one request per repo)")
    parser.add_argument("--max-repos", type=int, default=30, help="repos to read with --bytes (30)")
    parser.add_argument("--include-forks", action="store_true", help="count forked repos too")
    parser.add_argument("--skip-archived", action="store_true", help="leave archived repos out")
    args = parser.parse_args(argv)
    if not (args.user or args.from_file):
        parser.error("give a user name or --from-file FILE")
    if args.bytes and args.from_file:
        parser.error("--bytes needs to ask GitHub, so give a user name instead of --from-file")

    try:
        repos = (json.loads(args.from_file.read_text(encoding="utf-8")) if args.from_file
                 else api_get(f"/users/{args.user}/repos", {"per_page": 100, "type": "owner"}, 5))
        if not isinstance(repos, list):
            raise ValueError("that isn't a list of repositories")
        if args.bytes:
            totals, unit = bytes_by_language(repos, max(args.max_repos, 1)), "bytes"
        else:
            totals = tally(repos, args.weight, args.include_forks, not args.skip_archived)
            unit = {"count": "repo(s)", "stars": "star(s)", "size": "KB"}[args.weight]
    except urllib.error.HTTPError as err:
        print(f"GitHub said {err.code} ({'not found' if err.code == 404 else err.reason}).",
              file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"Couldn't get the data: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1

    if not totals:
        print("No language information found.")
        return 1
    print(f"Languages by {'code bytes' if args.bytes else args.weight}:\n")
    print(render(totals, unit))
    return 0


if __name__ == "__main__":
    sys.exit(main())
