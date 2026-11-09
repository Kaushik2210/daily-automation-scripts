"""Find merged branches nobody has touched for a while, and delete them only with --apply."""
import argparse
import subprocess  # web-ok: git only runs when you don't pass --refs and --merged files
import sys
from datetime import date
from pathlib import Path

US = "\x1f"
REF_FORMAT = "%(refname:short)%1f%(committerdate:short)%1f%(authorname)%1f%(subject)"
PROTECTED = {"main", "master", "develop", "dev", "trunk", "HEAD"}


def parse_refs(text, strip_prefix=""):
    """Parse `git for-each-ref` output (name, date, author, subject separated by \\x1f)."""
    branches = []
    for line in text.splitlines():
        parts = (line.split(US) + [""] * 4)[:4]
        name = parts[0].strip()
        if strip_prefix and name.startswith(strip_prefix):
            name = name[len(strip_prefix):]
        if name and name != "HEAD":
            branches.append({"name": name, "date": parts[1], "author": parts[2],
                             "subject": parts[3]})
    return branches


def parse_merged(text, strip_prefix=""):
    names = set()
    for line in text.splitlines():
        name = line.strip().lstrip("*+ ").strip()
        if " -> " in name:
            continue
        if strip_prefix and name.startswith(strip_prefix):
            name = name[len(strip_prefix):]
        if name:
            names.add(name)
    return names


def select_candidates(branches, merged, today, days, protected=frozenset(PROTECTED)):
    """Return (stale merged branches, skipped branches with reasons)."""
    chosen, skipped = [], []
    for branch in branches:
        try:
            age = (today - date.fromisoformat(branch["date"])).days
        except ValueError:
            skipped.append((branch["name"], "no readable commit date"))
            continue
        branch["age"] = age
        if branch["name"] in protected:
            skipped.append((branch["name"], "protected"))
        elif branch["name"] not in merged:
            skipped.append((branch["name"], "not merged into the base branch"))
        elif age < days:
            skipped.append((branch["name"], f"merged but only {age} day(s) old"))
        else:
            chosen.append(branch)
    return sorted(chosen, key=lambda b: -b["age"]), skipped


def git(repo, *args):
    try:
        proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                              encoding="utf-8", check=True)
    except (OSError, subprocess.CalledProcessError) as err:
        detail = getattr(err, "stderr", "") or err
        raise ValueError(f"git {' '.join(args[:2])} failed: {str(detail).strip()}") from err
    return proc.stdout


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Find and optionally delete stale merged branches.")
    parser.add_argument("--repo", type=Path, default=Path("."), help="git repository (default: .)")
    parser.add_argument("--base", default="main", help="branch the others must be merged into")
    parser.add_argument("--days", type=int, default=90, help="minimum days since last commit (90)")
    parser.add_argument("--remote", action="store_true", help="work on origin's branches instead")
    parser.add_argument("--refs", type=Path, help="saved for-each-ref output instead of git")
    parser.add_argument("--merged", type=Path, help="saved list of merged branch names")
    parser.add_argument("--today", help="treat this date as today, YYYY-MM-DD (for testing)")
    parser.add_argument("--apply", action="store_true", help="actually delete the branches")
    args = parser.parse_args(argv)
    if bool(args.refs) != bool(args.merged):
        parser.error("--refs and --merged go together")
    if args.apply and args.refs:
        parser.error("--apply needs a real repository, not saved files")
    try:
        today = date.fromisoformat(args.today) if args.today else date.today()
    except ValueError:
        parser.error("--today must look like 2026-11-09")

    prefix = "origin/" if args.remote else ""
    try:
        if args.refs:
            branches = parse_refs(args.refs.read_text(encoding="utf-8"), prefix)
            merged = parse_merged(args.merged.read_text(encoding="utf-8"), prefix)
            current = ""
        else:
            area = "refs/remotes/origin" if args.remote else "refs/heads"
            branches = parse_refs(git(args.repo, "for-each-ref", f"--format={REF_FORMAT}", area),
                                  prefix)
            target = f"origin/{args.base}" if args.remote else args.base
            flags = ["-r"] if args.remote else []
            merged = parse_merged(git(args.repo, "branch", *flags, "--merged", target), prefix)
            current = git(args.repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    except (OSError, ValueError) as err:
        print(f"Couldn't read the branches: {err}", file=sys.stderr)
        return 1

    protected = set(PROTECTED) | {args.base, current}
    chosen, skipped = select_candidates(branches, merged, today, args.days, frozenset(protected))
    where = "remote" if args.remote else "local"
    print(f"{len(chosen)} stale merged {where} branch(es) (merged into {args.base}, "
          f"idle {args.days}+ days) out of {len(branches)}:")
    for branch in chosen:
        print(f"  {branch['name']:<28} {branch['age']:>4} days  {branch['author']}")
    if not args.apply:
        print("\nDry run - nothing deleted. Add --apply to delete the branches listed above.")
        return 0
    failed = 0
    for branch in chosen:
        command = (["push", "origin", "--delete", branch["name"]] if args.remote
                   else ["branch", "-d", branch["name"]])
        try:
            git(args.repo, *command)
            print(f"deleted {branch['name']}")
        except ValueError as err:
            failed += 1
            print(f"could not delete {branch['name']}: {err}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
