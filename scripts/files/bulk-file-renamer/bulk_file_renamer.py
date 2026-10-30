"""Rename many files at once: find/replace, prefix/suffix or sequential numbering."""
import argparse
import sys
from pathlib import Path


def plan_renames(files, find="", replace="", prefix="", suffix="", number=False,
                 start=1, digits=3):
    """Return a list of (source, destination) pairs for files whose name would change."""
    plan = []
    for offset, path in enumerate(files):
        stem = path.stem.replace(find, replace) if find else path.stem
        stem = f"{prefix}{stem}{suffix}"
        if number:
            stem = f"{stem}_{start + offset:0{digits}d}"
        target = path.with_name(stem + path.suffix)
        if target != path:
            plan.append((path, target))
    return plan


def find_conflicts(plan):
    """Return destinations that collide with each other or with an unrelated file."""
    sources = {src for src, _ in plan}
    seen, conflicts = set(), []
    for _, dst in plan:
        if dst in seen or (dst.exists() and dst not in sources):
            conflicts.append(dst)
        seen.add(dst)
    return conflicts


def main(argv=None):
    parser = argparse.ArgumentParser(description="Bulk rename files in a folder.")
    parser.add_argument("folder", type=Path, help="folder containing the files")
    parser.add_argument("--pattern", default="*", help="glob of files to rename (default: *)")
    parser.add_argument("--find", default="", help="text to look for in file names")
    parser.add_argument("--replace", default="", help="text that replaces --find")
    parser.add_argument("--prefix", default="", help="text added before the name")
    parser.add_argument("--suffix", default="", help="text added after the name")
    parser.add_argument("--number", action="store_true", help="append a sequence number")
    parser.add_argument("--start", type=int, default=1, help="first sequence number")
    parser.add_argument("--digits", type=int, default=3, help="zero-padding for numbers")
    parser.add_argument("--apply", action="store_true",
                        help="really rename files (default is a dry run)")
    args = parser.parse_args(argv)

    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")
    files = sorted(p for p in args.folder.glob(args.pattern) if p.is_file())
    plan = plan_renames(files, args.find, args.replace, args.prefix, args.suffix,
                        args.number, args.start, args.digits)
    if not plan:
        print("Nothing to rename.")
        return 0
    conflicts = find_conflicts(plan)
    if conflicts:
        print("Stopping, these names would collide:", file=sys.stderr)
        for path in conflicts:
            print(f"  {path.name}", file=sys.stderr)
        return 1

    for src, dst in plan:
        print(f"{src.name} -> {dst.name}")
        if args.apply:
            src.rename(dst)
    verb = "Renamed" if args.apply else "Would rename"
    print(f"{verb} {len(plan)} file(s)." + ("" if args.apply else " Use --apply to do it."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
