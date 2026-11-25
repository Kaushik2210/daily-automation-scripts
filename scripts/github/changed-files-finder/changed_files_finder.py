"""List the files changed since a git ref and which monorepo projects they belong to."""
import argparse
import fnmatch
import json
import subprocess  # web-ok: git is only run without --from-file; saved diffs work anywhere
import sys
from pathlib import Path

STATUS = {"A": "added", "M": "modified", "D": "deleted", "R": "renamed", "C": "copied",
          "T": "type changed", "U": "unmerged"}


def parse_name_status(text):
    """Parse `git diff --name-status` into [{status, path, old_path}]."""
    changes = []
    for line in text.splitlines():
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 2 or not parts[0].strip():
            continue
        code = parts[0].strip()[0]
        if code in ("R", "C") and len(parts) >= 3:
            changes.append({"status": STATUS[code], "path": parts[2], "old_path": parts[1]})
        else:
            changes.append({"status": STATUS.get(code, "modified"), "path": parts[1],
                            "old_path": None})
    return changes


def project_of(path, patterns):
    """The project folder a path belongs to: 'apps/web' for 'apps/web/src/a.ts' with 'apps/*'."""
    parts = path.split("/")
    for pattern in patterns:
        depth = pattern.rstrip("/").count("/") + 1
        if len(parts) > depth and fnmatch.fnmatch("/".join(parts[:depth]), pattern.rstrip("/")):
            return "/".join(parts[:depth])
    return "(root)" if len(parts) == 1 else None


def group(changes, patterns):
    """{project: [changes]}; paths in no project fall under their top-level folder."""
    groups = {}
    for change in changes:
        for path in filter(None, [change["path"], change["old_path"]]):
            name = project_of(path, patterns) if patterns else None
            if name is None:
                name = path.split("/")[0] if "/" in path else "(root)"
            groups.setdefault(name, [])
            if change not in groups[name]:
                groups[name].append(change)
    return dict(sorted(groups.items()))


def add_dependents(projects, depends):
    """depends: {library: [projects that use it]}. Return (all affected, {project: reason})."""
    affected, reasons = set(projects), {}
    for library in list(projects):
        for user in depends.get(library, []):
            if user not in affected:
                affected.add(user)
                reasons[user] = f"depends on {library}"
    return sorted(affected), reasons


def git_changes(repo, ref, include_uncommitted):
    def run(*args):
        result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                                timeout=120, check=False)
        if result.returncode:
            raise OSError((result.stderr.strip().splitlines() or ["git failed"])[-1])
        return result.stdout
    text = run("diff", "--name-status", "-M", f"{ref}...HEAD")
    if include_uncommitted:
        text += run("diff", "--name-status", "-M", "HEAD")
        text += "".join(f"A\t{line[3:]}\n" for line in run("status", "--porcelain").splitlines()
                        if line.startswith("??"))
    return parse_name_status(text)


def main(argv=None):
    parser = argparse.ArgumentParser(description="List changed paths since a git ref.")
    parser.add_argument("--ref", default="origin/main", help="compare with this ref (origin/main)")
    parser.add_argument("--repo", type=Path, default=Path("."), help="the repository (.)")
    parser.add_argument("--from-file", type=Path, dest="source",
                        help="read saved `git diff --name-status` output instead of running git")
    parser.add_argument("--projects", nargs="*", default=[], metavar="PATTERN",
                        help="project folders, e.g. 'apps/*' 'libs/*' 'services/*'")
    parser.add_argument("--depends", action="append", default=[], metavar="LIB=USER,USER",
                        help="projects affected when a library changes, e.g. libs/shared=apps/web")
    parser.add_argument("--exclude", action="append", default=[], help="ignore paths matching this")
    parser.add_argument("--ext", help="only these extensions, e.g. py,ts")
    parser.add_argument("--include-uncommitted", action="store_true",
                        help="also count uncommitted and new files")
    parser.add_argument("--format", choices=["text", "json", "paths", "projects"], default="text")
    args = parser.parse_args(argv)

    depends = {}
    for item in args.depends:
        library, _, users = item.partition("=")
        if not users:
            parser.error(f"--depends needs LIB=USER[,USER], got '{item}'")
        depends.setdefault(library.strip(), []).extend(u.strip() for u in users.split(","))
    try:
        changes = (parse_name_status(args.source.read_text(encoding="utf-8")) if args.source
                   else git_changes(args.repo, args.ref, args.include_uncommitted))
    except (OSError, subprocess.SubprocessError) as err:
        print(f"Can't get the changes: {err}", file=sys.stderr)
        return 1
    exts = {"." + e.strip(". ") for e in args.ext.split(",")} if args.ext else None
    changes = [c for c in changes
               if not any(fnmatch.fnmatch(c["path"], pat) for pat in args.exclude)
               and (exts is None or Path(c["path"]).suffix in exts)]

    groups = group(changes, args.projects)
    affected, reasons = add_dependents([p for p in groups if p != "(root)"], depends)
    if args.format == "paths":
        print("\n".join(sorted({c["path"] for c in changes if c["status"] != "deleted"})))
    elif args.format == "projects":
        print("\n".join(affected))
    elif args.format == "json":
        print(json.dumps({"files": [c["path"] for c in changes], "changes": changes,
                          "projects": affected, "reasons": reasons}, indent=1))
    else:
        source = f"saved diff {args.source.name}" if args.source else f"{args.ref}...HEAD"
        print(f"{len(changes)} changed file(s) in {source}\n")
        for name, items in groups.items():
            print(f"{name}  ({len(items)})")
            for item in items:
                moved = f" (from {item['old_path']})" if item["old_path"] else ""
                print(f"  {item['status']:<12} {item['path']}{moved}")
        if reasons:
            print("\nAlso affected through dependencies:")
            print("\n".join(f"  {name}  ({why})" for name, why in sorted(reasons.items())))
        counts = {}
        for item in changes:
            counts[item["status"]] = counts.get(item["status"], 0) + 1
        print("\n" + ", ".join(f"{n} {s}" for s, n in sorted(counts.items())) + "."
              if counts else "\nNo changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
