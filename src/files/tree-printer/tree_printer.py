"""Print a directory tree with an optional depth limit."""
import argparse
import sys
from pathlib import Path

UNICODE = ("├── ", "└── ", "│   ", "    ")
ASCII = ("|-- ", "`-- ", "|   ", "    ")


def build_tree(root, max_depth=None, show_hidden=False, dirs_only=False, chars=UNICODE):
    """Return the tree as a list of text lines."""
    branch, last, pipe, blank = chars
    lines = [Path(root).name or str(root)]

    def walk(folder, prefix, depth):
        if max_depth is not None and depth > max_depth:
            return
        try:
            children = sorted(folder.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            return
        children = [c for c in children if show_hidden or not c.name.startswith(".")]
        if dirs_only:
            children = [c for c in children if c.is_dir()]
        for index, child in enumerate(children):
            is_last = index == len(children) - 1
            lines.append(prefix + (last if is_last else branch) + child.name)
            if child.is_dir() and not child.is_symlink():
                walk(child, prefix + (blank if is_last else pipe), depth + 1)

    walk(Path(root), "", 1)
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description="Print a directory tree.")
    parser.add_argument("folder", type=Path, nargs="?", default=Path("."))
    parser.add_argument("-d", "--depth", type=int, help="maximum depth to show")
    parser.add_argument("-a", "--all", action="store_true", help="include hidden files")
    parser.add_argument("--dirs-only", action="store_true", help="show folders only")
    parser.add_argument("--ascii", action="store_true", help="use plain ASCII lines")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")

    chars = ASCII if args.ascii else UNICODE
    try:
        "".join(chars).encode(sys.stdout.encoding or "utf-8")
    except UnicodeEncodeError:
        chars = ASCII
    print("\n".join(build_tree(args.folder, args.depth, args.all, args.dirs_only, chars)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
