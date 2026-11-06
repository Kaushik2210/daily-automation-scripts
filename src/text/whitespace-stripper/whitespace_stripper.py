"""Strip trailing whitespace and normalize line endings in text files."""
import argparse
import sys
from pathlib import Path

EOLS = {"lf": "\n", "crlf": "\r\n"}


def clean_text(text, eol="keep", final_newline=True):
    """Return text without trailing spaces, with consistent line endings."""
    if eol == "keep":
        eol = "crlf" if "\r\n" in text else "lf"
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    result = EOLS[eol].join(lines)
    return result + EOLS[eol] if final_newline and lines else result


def collect_files(paths, pattern):
    files = []
    for path in paths:
        files.extend(sorted(p for p in path.rglob(pattern) if p.is_file()) if path.is_dir()
                     else [path])
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description="Strip trailing whitespace from text files.")
    parser.add_argument("paths", nargs="+", type=Path, help="files or folders")
    parser.add_argument("--pattern", default="*.txt", help="files to match in folders (*.txt)")
    parser.add_argument("--eol", choices=["keep", "lf", "crlf"], default="keep",
                        help="line ending to use (default: keep what the file mostly uses)")
    parser.add_argument("--no-final-newline", action="store_true",
                        help="don't force a newline at the end of the file")
    parser.add_argument("--apply", action="store_true",
                        help="really rewrite files (default is a dry run)")
    args = parser.parse_args(argv)

    changed = 0
    for path in collect_files(args.paths, args.pattern):
        try:
            original = path.read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError):
            print(f"skip {path}: not readable as UTF-8 text")
            continue
        cleaned = clean_text(original, args.eol, not args.no_final_newline)
        if cleaned == original:
            continue
        print(f"{path}")
        if args.apply:
            path.write_bytes(cleaned.encode("utf-8"))
        changed += 1
    verb = "Cleaned" if args.apply else "Would clean"
    hint = "" if args.apply else " Use --apply to do it."
    print(f"{verb} {changed} file(s).{hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
