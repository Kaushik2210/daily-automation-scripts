"""Find and replace text across many files, with a dry run first."""
import argparse
import re
import sys
from pathlib import Path


def replace_text(text, find, replace, use_regex=False, ignore_case=False):
    """Return (new_text, number_of_replacements)."""
    pattern = find if use_regex else re.escape(find)
    flags = re.IGNORECASE if ignore_case else 0
    if use_regex:
        return re.subn(pattern, replace, text, flags=flags)
    return re.subn(pattern, lambda _: replace, text, flags=flags)


def collect_files(folder, pattern):
    return sorted(p for p in Path(folder).rglob(pattern) if p.is_file())


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find and replace text in many files.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--find", required=True, help="text (or regex) to look for")
    parser.add_argument("--replace", default="", help="replacement text (default: nothing)")
    parser.add_argument("--pattern", default="*", help="which files to search (default: *)")
    parser.add_argument("--regex", action="store_true", help="treat --find as a regex")
    parser.add_argument("-i", "--ignore-case", action="store_true", help="ignore letter case")
    parser.add_argument("--apply", action="store_true",
                        help="really change files (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")
    try:
        re.compile(args.find if args.regex else "")
    except re.error as err:
        parser.error(f"bad regex: {err}")

    files_changed = total = 0
    for path in collect_files(args.folder, args.pattern):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        new_text, count = replace_text(text, args.find, args.replace, args.regex,
                                       args.ignore_case)
        if count:
            print(f"{path}: {count} replacement(s)")
            if args.apply:
                path.write_text(new_text, encoding="utf-8")
            files_changed += 1
            total += count
    verb = "Replaced" if args.apply else "Would replace"
    hint = "" if args.apply else " Use --apply to do it."
    print(f"{verb} {total} occurrence(s) in {files_changed} file(s).{hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
