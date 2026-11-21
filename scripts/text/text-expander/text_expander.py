"""Expand abbreviations (btw, ;sig, addr) in text files using a map file."""
import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path


def load_map(path):
    """Read 'abbr = text' lines (\\n for a new line) or a JSON object into {abbr: text}."""
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("the JSON map must be an object of abbreviation: text")
        return {str(k): str(v) for k, v in data.items()}
    mapping = {}
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep or not key.strip():
            raise ValueError(f"line {number}: expected 'abbreviation = text'")
        mapping[key.strip()] = value.strip().replace("\\n", "\n")
    return mapping


def fill(text, now=None):
    now = now or datetime.now()
    return (text.replace("{datetime}", f"{now:%Y-%m-%d %H:%M}").replace("{date}", f"{now:%Y-%m-%d}")
            .replace("{time}", f"{now:%H:%M}"))


def expand(text, mapping, ignore_case=False, now=None):
    """Return (new text, {abbreviation: times replaced}). Longest abbreviations win."""
    if not mapping:
        return text, {}
    keys = sorted(mapping, key=len, reverse=True)
    flags = re.IGNORECASE if ignore_case else 0
    pattern = re.compile("(?<!\\w)(" + "|".join(re.escape(k) for k in keys) + ")(?!\\w)", flags)
    lookup = {k.lower(): v for k, v in mapping.items()} if ignore_case else mapping
    counts = {}

    def replace(match):
        found = match.group(1)
        key = found.lower() if ignore_case else found
        original = next(k for k in mapping if k.lower() == key) if ignore_case else found
        counts[original] = counts.get(original, 0) + 1
        return fill(lookup[key], now)

    return pattern.sub(replace, text), counts


def backup_name(path):
    candidate = path.with_name(path.name + ".bak")
    if candidate.exists():
        candidate = path.with_name(f"{path.name}.{time.strftime('%Y%m%d-%H%M%S')}.bak")
    return candidate


def main(argv=None):
    parser = argparse.ArgumentParser(description="Expand abbreviations in text files.")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--map", type=Path, required=True,
                        help="abbreviation map: 'abbr = text' lines or a JSON object")
    parser.add_argument("--ignore-case", action="store_true", help="match BTW and btw alike")
    parser.add_argument("--apply", action="store_true",
                        help="really change the files (default is a dry run); a .bak copy is kept")
    args = parser.parse_args(argv)
    try:
        mapping = load_map(args.map)
    except (OSError, ValueError) as err:
        print(f"Can't read the map: {err}", file=sys.stderr)
        return 1
    if not mapping:
        print("The map is empty.", file=sys.stderr)
        return 1

    changed_files = 0
    for path in args.files:
        if not path.is_file():
            print(f"not found: {path}", file=sys.stderr)
            continue
        original = path.read_text(encoding="utf-8")
        result, counts = expand(original, mapping, args.ignore_case)
        if not counts:
            print(f"{path.name}: nothing to expand")
            continue
        detail = ", ".join(f"{k} x{n}" for k, n in sorted(counts.items()))
        print(f"{path.name}: {sum(counts.values())} replacement(s) ({detail})")
        if args.apply:
            backup = backup_name(path)
            backup.write_text(original, encoding="utf-8")
            path.write_text(result, encoding="utf-8")
            print(f"  saved; the original is kept as {backup.name}")
        else:
            for before, after in zip(original.splitlines(), result.splitlines(), strict=False):
                if before != after:
                    print(f"  - {before}\n  + {after}")
                    break
        changed_files += 1
    if not args.apply and changed_files:
        print("\nDry run. Use --apply to change the files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
