"""Clean up messy file names: lowercase, no spaces, no odd characters."""
import argparse
import re
import sys
from pathlib import Path


def normalize(name, sep="_"):
    """Return a tidy version of a file name; the extension is lowercased and kept."""
    path = Path(name)
    stem = re.sub(r"[^\w\s.-]", "", path.stem.lower())
    stem = re.sub(r"[\s_.-]+", sep, stem).strip(sep)
    return (stem or "file") + path.suffix.lower()


def plan_renames(folder, recursive=False, sep="_"):
    pattern = "**/*" if recursive else "*"
    plan = []
    for path in sorted(Path(folder).glob(pattern)):
        if path.is_file():
            new = path.with_name(normalize(path.name, sep))
            if new.name != path.name:
                plan.append((path, new))
    return plan


def main(argv=None):
    parser = argparse.ArgumentParser(description="Normalize file names in a folder.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("-r", "--recursive", action="store_true", help="include subfolders")
    parser.add_argument("--sep", default="_", choices=["_", "-"], help="word separator")
    parser.add_argument("--apply", action="store_true",
                        help="really rename files (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")

    done = 0
    for src, dst in plan_renames(args.folder, args.recursive, args.sep):
        if dst.exists() and dst != src:
            print(f"skip {src.name}: {dst.name} already exists")
            continue
        print(f"{src.name} -> {dst.name}")
        if args.apply:
            src.rename(dst)
        done += 1
    verb = "Renamed" if args.apply else "Would rename"
    hint = "" if args.apply else " Use --apply to do it."
    print(f"{verb} {done} file(s).{hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
