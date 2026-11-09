"""Rank the contributors of a GitHub repository by number of commits."""
import argparse
import json
import os
import re
import sys
import urllib.error  # web-ok: the network is only used when you name a repository
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

API = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
USER_AGENT = "daily-automation-scripts/1.0 (contributor leaderboard)"


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
            body, link = r.read(), r.headers.get("Link", "")
        data = json.loads(body) if body.strip() else []
        if not isinstance(data, list):
            return data
        items += data
        nxt = re.search(r'<([^>]+)>;\s*rel="next"', link)
        if not nxt or not nxt.group(1).startswith(API):
            break
        url = nxt.group(1)
    return items


def is_bot(entry):
    login = entry.get("login") or ""
    return entry.get("type") == "Bot" or login.endswith("[bot]")


def rank(entries, exclude_bots=False):
    """Return [(name, commits)] biggest first; anonymous contributors use their commit name."""
    rows = []
    for entry in entries:
        if exclude_bots and is_bot(entry):
            continue
        name = entry.get("login") or entry.get("name") or "(anonymous)"
        rows.append((name, int(entry.get("contributions", 0))))
    return sorted(rows, key=lambda r: (-r[1], r[0].casefold()))


def render(rows, top, width=24):
    total = sum(count for _, count in rows)
    shown = rows[:top]
    name_width = max(len(name) for name, _ in shown)
    lines, running = [], 0
    for place, (name, count) in enumerate(shown, 1):
        running += count
        bar = "#" * max(1, round(count / shown[0][1] * width)) if count else ""
        lines.append(f"{place:>3}. {name:<{name_width}}  {count:>6,}  {count / total:>6.1%}  {bar}")
    lines.append(f"\n{len(rows)} contributor(s), {total:,} commits. "
                 f"The top {len(shown)} wrote {running / total:.0%}.")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Rank a repository's contributors.")
    parser.add_argument("repo", nargs="?", help="owner/repo, e.g. octocat/Hello-World")
    parser.add_argument("--from-file", type=Path, help="read a saved API response instead")
    parser.add_argument("--top", type=int, default=10, help="how many to show (10)")
    parser.add_argument("--exclude-bots", action="store_true", help="leave out bot accounts")
    args = parser.parse_args(argv)
    if not (args.repo or args.from_file):
        parser.error("give owner/repo or --from-file FILE")
    if args.repo and not re.fullmatch(r"[\w.-]+/[\w.-]+", args.repo):
        parser.error("repo must look like owner/name")
    if args.top < 1:
        parser.error("--top must be at least 1")

    try:
        entries = (json.loads(args.from_file.read_text(encoding="utf-8")) if args.from_file
                   else api_get(f"/repos/{args.repo}/contributors",
                                {"per_page": 100, "anon": "1"}, 10))
    except urllib.error.HTTPError as err:
        hint = {404: "repository not found (or private - set GITHUB_TOKEN)", 403: "rate limit "
                "or access denied (very large repositories also refuse this list)"}
        print(f"GitHub said {err.code}: {hint.get(err.code, err.reason)}.", file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"Couldn't get the contributors: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1
    if not isinstance(entries, list):
        print("That doesn't look like a contributors list.", file=sys.stderr)
        return 1

    rows = rank(entries, args.exclude_bots)
    if not rows or sum(count for _, count in rows) == 0:
        print("No contributors found.")
        return 1
    print(render(rows, args.top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
