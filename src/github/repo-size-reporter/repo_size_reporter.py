"""Report how big a repository is and which files and file types take the most space."""
import argparse
import os
import sys
from pathlib import Path

SKIP_DIRS = {"node_modules", ".venv", "venv", "__pycache__"}


def human_size(num):
    size = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def measure(root, include_deps=False):
    """Walk `root` and return a dict with working tree, .git and per-file numbers."""
    root = Path(root)
    files, git_bytes, skipped = [], 0, 0
    for current, dirs, names in os.walk(root):
        here = Path(current)
        if here == root / ".git":
            git_bytes = sum(p.stat().st_size for p in here.rglob("*") if p.is_file())
            dirs[:] = []
            continue
        if not include_deps:
            skipped += sum(d in SKIP_DIRS for d in dirs)
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in names:
            path = here / name
            try:
                files.append((path.stat().st_size, path.relative_to(root).as_posix()))
            except OSError:
                continue
    by_ext = {}
    for size, rel in files:
        ext = Path(rel).suffix.lower() or "(none)"
        count, total = by_ext.get(ext, (0, 0))
        by_ext[ext] = (count + 1, total + size)
    return {"files": sorted(files, reverse=True), "git_bytes": git_bytes, "by_ext": by_ext,
            "skipped_dirs": skipped}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Report repository size.")
    parser.add_argument("folder", type=Path, nargs="?", default=Path("."))
    parser.add_argument("-n", "--top", type=int, default=5, help="how many big files to list (5)")
    parser.add_argument("--include-deps", action="store_true",
                        help="also count node_modules and virtual environments")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")

    report = measure(args.folder, args.include_deps)
    total = sum(size for size, _ in report["files"])
    print(f"Working tree: {human_size(total)} in {len(report['files'])} file(s)")
    if report["git_bytes"]:
        print(f".git history: {human_size(report['git_bytes'])}")
    if report["skipped_dirs"]:
        print(f"(skipped {report['skipped_dirs']} dependency folder(s); use --include-deps)")
    print(f"\nLargest {min(args.top, len(report['files']))} file(s):")
    for size, rel in report["files"][:args.top]:
        print(f"  {human_size(size):>9}  {rel}")
    print("\nBy file type:")
    ranked = sorted(report["by_ext"].items(), key=lambda kv: -kv[1][1])
    for ext, (count, size) in ranked[:8]:
        share = 100 * size / total if total else 0
        print(f"  {ext:<8}{count:>5} file(s)  {human_size(size):>9}  {share:>3.0f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
