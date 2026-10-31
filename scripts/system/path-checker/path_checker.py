"""Check the PATH variable for missing, duplicate and empty entries."""
import argparse
import os
import sys
from pathlib import Path


def normalize(entry):
    """Key used to spot duplicates: expanded, absolute, case-folded on Windows."""
    key = os.path.normpath(os.path.expandvars(os.path.expanduser(entry)))
    return key.lower() if os.name == "nt" else key


def analyze(entries):
    """Return a list of (position, entry, problem); problem is one of
    'empty', 'missing', 'not a folder' or 'duplicate'."""
    problems, seen = [], {}
    for position, entry in enumerate(entries, 1):
        if not entry.strip():
            problems.append((position, entry, "empty"))
            continue
        path = Path(os.path.expandvars(os.path.expanduser(entry)))
        key = normalize(entry)
        if key in seen:
            problems.append((position, entry, f"duplicate of #{seen[key]}"))
        else:
            seen[key] = position
        if not path.exists():
            problems.append((position, entry, "missing"))
        elif not path.is_dir():
            problems.append((position, entry, "not a folder"))
    return problems


def cleaned(entries):
    """PATH entries with empty, missing and repeated folders removed, order kept."""
    keep, seen = [], set()
    for entry in entries:
        if not entry.strip() or not Path(os.path.expandvars(os.path.expanduser(entry))).is_dir():
            continue
        key = normalize(entry)
        if key not in seen:
            seen.add(key)
            keep.append(entry)
    return keep


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check PATH for problems.")
    parser.add_argument("--path", help="check this PATH string instead of the real one")
    parser.add_argument("--suggest", action="store_true",
                        help="also print a cleaned-up PATH value (nothing is changed)")
    args = parser.parse_args(argv)

    entries = (args.path if args.path is not None else os.environ.get("PATH", "")).split(os.pathsep)
    problems = analyze(entries)
    for position, entry, problem in problems:
        print(f"#{position:<3} {problem:<16} {entry or '(blank)'}")
    print(f"{len(entries)} entries, {len(problems)} problem(s).")
    if args.suggest and problems:
        print("\nCleaned PATH:")
        print(os.pathsep.join(cleaned(entries)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
