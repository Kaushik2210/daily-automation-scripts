"""Add a license header (copyright + SPDX id) to the source files of a project; dry run first."""
import argparse
import re
import sys
from datetime import date
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".tox",
             "target", "vendor"}
HASH, SLASH, DASH = ("#", None), ("//", None), ("--", None)
STYLES = {".py": HASH, ".sh": HASH, ".rb": HASH, ".pl": HASH, ".r": HASH, ".yml": HASH,
          ".yaml": HASH, ".js": SLASH, ".jsx": SLASH, ".ts": SLASH, ".tsx": SLASH, ".java": SLASH,
          ".c": SLASH, ".h": SLASH, ".cpp": SLASH, ".hpp": SLASH, ".cs": SLASH, ".go": SLASH,
          ".rs": SLASH, ".kt": SLASH, ".swift": SLASH, ".scss": SLASH, ".sql": DASH, ".lua": DASH,
          ".css": ("/*", " */"), ".html": ("<!--", "-->"), ".xml": ("<!--", "-->")}
LICENSES = {
    "mit": ("MIT", "Licensed under the MIT License. See the LICENSE file in the project root."),
    "apache-2.0": ("Apache-2.0", "Licensed under the Apache License, Version 2.0. See the "
                                 "LICENSE file in the project root."),
    "gpl-3.0": ("GPL-3.0-or-later", "Licensed under the GNU General Public License v3.0 or "
                                    "later. See the LICENSE file in the project root."),
    "bsd-3-clause": ("BSD-3-Clause", "Licensed under the BSD 3-Clause License. See the LICENSE "
                                     "file in the project root."),
    "isc": ("ISC", "Licensed under the ISC License. See the LICENSE file in the project root."),
    "unlicense": ("Unlicense", "This is free and unencumbered software released into the public "
                               "domain."),
}
HEADER_MARKERS = re.compile(r"SPDX-License-Identifier|copyright|licensed under", re.IGNORECASE)


def header_lines(license_key, holder, year, custom=None):
    if custom:
        return custom.strip("\n").splitlines()
    spdx, sentence = LICENSES[license_key]
    return [f"Copyright (c) {year} {holder}", sentence, f"SPDX-License-Identifier: {spdx}"]


def comment_block(lines, style):
    start, end = style
    if end is None:
        return [f"{start} {line}".rstrip() for line in lines]
    if start == "/*":
        return ["/*", *[f" * {line}".rstrip() for line in lines], end]
    return [start, *[f"  {line}".rstrip() for line in lines], end]


def split_preamble(text, suffix):
    """Return (preamble lines to keep first, rest of the lines)."""
    lines = text.split("\n")
    keep = 0
    if suffix in (".py", ".sh", ".rb", ".pl", ".r") and lines and lines[0].startswith("#!"):
        keep = 1
    if suffix == ".py" and len(lines) > keep and re.match(r"#.*coding[:=]\s*[-\w.]+", lines[keep]):
        keep += 1
    if suffix in (".html", ".xml") and lines and re.match(r"\s*<(\?xml|!doctype)", lines[0],
                                                          re.IGNORECASE):
        keep = 1
    return lines[:keep], lines[keep:]


def has_header(text):
    return bool(HEADER_MARKERS.search("\n".join(text.split("\n")[:12])))


def add_header(text, suffix, lines):
    """Return the file text with the header inserted, or None when it already has one."""
    if has_header(text):
        return None
    newline = "\r\n" if "\r\n" in text else "\n"
    body = text.replace("\r\n", "\n")
    preamble, rest = split_preamble(body, suffix)
    block = comment_block(lines, STYLES[suffix])
    gap = [""] if rest and rest[0].strip() else []
    return newline.join([*preamble, *block, *gap, *rest])


def find_files(paths, suffixes):
    files = []
    for path in paths:
        if path.is_file():
            files.append(path)
            continue
        for candidate in sorted(path.rglob("*")):
            if candidate.is_file() and candidate.suffix.lower() in suffixes and not any(
                    part in SKIP_DIRS for part in candidate.relative_to(path).parts[:-1]):
                files.append(candidate)
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description="Add license headers to source files.")
    parser.add_argument("paths", nargs="+", type=Path, help="files or folders")
    parser.add_argument("--license", choices=sorted(LICENSES), default="mit", help="license (mit)")
    parser.add_argument("--holder", default="The Authors", help="copyright holder name")
    parser.add_argument("--year", default=str(date.today().year), help="copyright year")
    parser.add_argument("--text-file", type=Path, help="use this text as the header instead")
    parser.add_argument("--ext", help="only these extensions, e.g. py,js (default: all known)")
    parser.add_argument("--apply", action="store_true",
                        help="really change the files (default is a dry run)")
    args = parser.parse_args(argv)
    for path in args.paths:
        if not path.exists():
            parser.error(f"not found: {path}")
    suffixes = {"." + e.strip(". ").lower() for e in args.ext.split(",")} if args.ext else set(
        STYLES)
    unknown = suffixes - set(STYLES)
    if unknown:
        parser.error(f"no comment style known for: {', '.join(sorted(unknown))}")
    custom = args.text_file.read_text(encoding="utf-8") if args.text_file else None

    lines = header_lines(args.license, args.holder, args.year, custom)
    changed = skipped = failed = 0
    for path in find_files(args.paths, suffixes):
        suffix = path.suffix.lower()
        if suffix not in STYLES:
            print(f"skip {path}: no comment style for {suffix or 'this file type'}")
            skipped += 1
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            print(f"skip {path}: can't read it as text")
            failed += 1
            continue
        result = add_header(text, suffix, lines)
        if result is None:
            print(f"has header   {path}")
            skipped += 1
            continue
        print(f"{'added' if args.apply else 'would add'}  {path}")
        changed += 1
        if args.apply:
            path.write_bytes(result.encode("utf-8"))
    verb = "Added headers to" if args.apply else "Would add headers to"
    print(f"\n{verb} {changed} file(s); {skipped} already had one or were skipped"
          + (f"; {failed} unreadable" if failed else "") + "."
          + ("" if args.apply or not changed else " Use --apply to do it."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
