"""Compare issue labels across GitHub repositories and report the differences."""
import argparse
import json
import os
import re
import sys
import urllib.error  # web-ok: the network is only used when you name repositories
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

API = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
USER_AGENT = "daily-automation-scripts/1.0 (label auditor)"


def fetch_labels(repo):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT,
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{API}/repos/{repo}/labels?" + urlencode({"per_page": 100})
    labels = []
    for _ in range(5):
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as r:
            labels += json.loads(r.read())
            link = r.headers.get("Link", "")
        nxt = re.search(r'<([^>]+)>;\s*rel="next"', link)
        if not nxt or not nxt.group(1).startswith(API):
            break
        url = nxt.group(1)
    return labels


def normalise(name):
    return re.sub(r"[^a-z0-9]+", "", name.casefold())


def audit(by_repo):
    """Compare {repo: [label dicts]} and return a dict of findings."""
    repos = list(by_repo)
    table = {}  # normalised name -> {repo: label}
    for repo, labels in by_repo.items():
        for label in labels:
            table.setdefault(normalise(label.get("name", "")), {})[repo] = label
    findings = {"missing": [], "case": [], "color": [], "description": []}
    for _key, present in sorted(table.items()):
        shown = min({lab["name"] for lab in present.values()}, key=lambda n: (n.casefold(), n))
        absent = [r for r in repos if r not in present]
        if absent:
            findings["missing"].append((shown, absent, [r for r in repos if r in present]))
        names = {lab["name"] for lab in present.values()}
        if len(names) > 1:
            findings["case"].append((shown, {r: lab["name"] for r, lab in present.items()}))
        colors = {(lab.get("color") or "").lower() for lab in present.values()}
        if len(colors) > 1:
            findings["color"].append((shown, {r: (lab.get("color") or "").lower()
                                              for r, lab in present.items()}))
        descriptions = {(lab.get("description") or "").strip() for lab in present.values()}
        if len(descriptions) > 1:
            findings["description"].append((shown, {r: (lab.get("description") or "").strip()
                                                    for r, lab in present.items()}))
    return findings, len(table)


def report(findings, total, repos):
    lines = [f"Compared {len(repos)} repositories and {total} distinct label(s).\n"]
    sections = [("Missing from some repositories", "missing"),
                ("Same label spelled differently", "case"),
                ("Different colours", "color"), ("Different descriptions", "description")]
    problems = 0
    for title, key in sections:
        items = findings[key]
        problems += len(items)
        if not items:
            continue
        lines.append(f"{title} ({len(items)}):")
        for item in items:
            if key == "missing":
                name, absent, _present = item
                lines.append(f"  {name!r}: missing in {', '.join(absent)}")
            else:
                name, values = item
                detail = "; ".join(f"{repo.split('/')[-1]}={value or '(none)'}"
                                   for repo, value in values.items())
                lines.append(f"  {name!r}: {detail}")
        lines.append("")
    lines.append("All labels match." if not problems else f"{problems} difference(s) found.")
    return "\n".join(lines), problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare issue labels across repositories.")
    parser.add_argument("repos", nargs="*", help="repositories as owner/name (at least two)")
    parser.add_argument("--from-file", type=Path,
                        help="read saved labels ({repo: [labels]}) instead of asking GitHub")
    args = parser.parse_args(argv)
    if not (args.repos or args.from_file):
        parser.error("give two or more repositories, or --from-file FILE")
    bad = [r for r in args.repos if not re.fullmatch(r"[\w.-]+/[\w.-]+", r)]
    if bad:
        parser.error(f"not an owner/name repository: {bad[0]}")

    try:
        if args.from_file:
            by_repo = json.loads(args.from_file.read_text(encoding="utf-8"))
            if not isinstance(by_repo, dict):
                raise ValueError("expected an object mapping repository to labels")
        else:
            by_repo = {repo: fetch_labels(repo) for repo in args.repos}
    except urllib.error.HTTPError as err:
        print(f"GitHub said {err.code} ({'not found' if err.code == 404 else err.reason}).",
              file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"Couldn't get the labels: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1
    if len(by_repo) < 2:
        print("Give at least two repositories to compare.", file=sys.stderr)
        return 1

    findings, total = audit(by_repo)
    text, problems = report(findings, total, list(by_repo))
    print(text)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
