"""Count commits and changed lines per author in a git repository."""
import argparse
import subprocess  # web-ok: git only runs when no --log file is given
import sys
from pathlib import Path

US = "\x1f"
LOG_FORMAT = "@@%H%x1f%an%x1f%ae%x1f%ad%x1f%s"


def parse_log(text):
    """Parse `git log --numstat` output in the format described in the README."""
    commits = []
    for line in text.splitlines():
        if line.startswith("@@"):
            sha, name, email, day, subject = (line[2:].split(US) + [""] * 5)[:5]
            commits.append({"name": name, "email": email, "date": day, "added": 0, "deleted": 0})
        elif commits and line.strip():
            parts = line.split("\t")
            if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():  # skips binary files
                commits[-1]["added"] += int(parts[0])
                commits[-1]["deleted"] += int(parts[1])
    return commits


def run_git(repo, *args):
    try:
        proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                              encoding="utf-8", check=True)
    except (OSError, subprocess.CalledProcessError) as err:
        raise SystemExit(f"Couldn't run git in {repo}: {err}") from err
    return proc.stdout


def author_stats(commits, key="name"):
    """Return a list of per-author dicts, one per distinct `key` ('name' or 'email')."""
    stats = {}
    for c in commits:
        s = stats.setdefault(c[key], {"author": c[key], "commits": 0, "added": 0, "deleted": 0,
                                      "days": set(), "first": c["date"], "last": c["date"]})
        s["commits"] += 1
        s["added"] += c["added"]
        s["deleted"] += c["deleted"]
        s["days"].add(c["date"])
        s["first"], s["last"] = min(s["first"], c["date"]), max(s["last"], c["date"])
    return list(stats.values())


def main(argv=None):
    parser = argparse.ArgumentParser(description="Commits and lines per author.")
    parser.add_argument("--repo", type=Path, default=Path("."), help="git repository (default: .)")
    parser.add_argument("--log", type=Path, help="read a saved git log --numstat file")
    parser.add_argument("--by", choices=["name", "email"], default="name", help="group authors by")
    parser.add_argument("--sort", choices=["commits", "lines"], default="commits")
    args = parser.parse_args(argv)
    if args.log and not args.log.is_file():
        parser.error(f"log file not found: {args.log}")

    if args.log:
        text = args.log.read_text(encoding="utf-8")
    else:
        text = run_git(args.repo, "log", "--numstat", "--date=short",
                       f"--pretty=format:{LOG_FORMAT}")
    commits = parse_log(text)
    if not commits:
        print("No commits found.")
        return 0
    rows = author_stats(commits, args.by)
    order = (lambda r: -(r["added"] + r["deleted"])) if args.sort == "lines" else (
        lambda r: -r["commits"])
    rows.sort(key=order)
    print(f"{'author':<18}{'commits':>8}{'share':>7}{'added':>8}{'deleted':>9}{'days':>6}  active")
    for r in rows:
        share = 100 * r["commits"] / len(commits)
        print(f"{r['author']:<18}{r['commits']:>8}{share:>6.0f}%{r['added']:>8}{r['deleted']:>9}"
              f"{len(r['days']):>6}  {r['first']} to {r['last']}")
    print(f"{len(commits)} commit(s), {len(rows)} author(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
