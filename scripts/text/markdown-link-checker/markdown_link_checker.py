"""Check the links inside markdown files: local files, #anchors and (optionally) web URLs."""
import argparse
import re
import sys
import urllib.error  # web-ok: web links are only requested with --external
import urllib.request
from pathlib import Path

INLINE = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+[\"'][^\"']*[\"'])?\s*\)")
REFERENCE_USE = re.compile(r"!?\[[^\]]+\]\[([^\]]*)\]")
REFERENCE_DEF = re.compile(r"^\s{0,3}\[([^\]]+)\]:\s*<?(\S+?)>?(?:\s+.*)?$")
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")
SKIP_SCHEMES = ("mailto:", "tel:", "javascript:", "data:")


def slugify(heading):
    """GitHub-style anchor for a heading."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"", heading.lower())  # keep link text only
    text = re.sub(r"[`*_]", "", text)
    text = re.sub(r"[^\w\- ]", "", text, flags=re.UNICODE)
    return text.strip().replace(" ", "-")


def scan(text):
    """Return (anchors, [(line number, link target)]) skipping code blocks and inline code."""
    anchors, seen, links, definitions, uses = set(), {}, [], {}, []
    in_fence = False
    for number, line in enumerate(text.splitlines(), 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        heading = HEADING.match(line)
        if heading:
            slug = slugify(heading.group(2))
            count = seen.get(slug, 0)
            seen[slug] = count + 1
            anchors.add(slug if not count else f"{slug}-{count}")
        definition = REFERENCE_DEF.match(line)
        if definition:
            definitions[definition.group(1).lower()] = (number, definition.group(2))
            continue
        plain = re.sub(r"`[^`]*`", "", line)
        links += [(number, m.group(1)) for m in INLINE.finditer(plain)]
        uses += [(number, m.group(1) or m.group(0)) for m in REFERENCE_USE.finditer(plain)]
    for number, label in uses:
        key = label.lower()
        if key in definitions:
            links.append((definitions[key][0], definitions[key][1]))
        else:
            links.append((number, f"[{label}]"))  # undefined reference
    return anchors, sorted(set(links))


def check_web(url, timeout):
    request = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "daily-automation-scripts/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout):
            return None
    except urllib.error.HTTPError as err:
        if err.code in (403, 405, 501):  # some servers refuse HEAD; try a normal request
            try:
                with urllib.request.urlopen(url, timeout=timeout):
                    return None
            except (urllib.error.URLError, OSError) as second:
                return str(getattr(second, "reason", second))
        return f"HTTP {err.code}"
    except (urllib.error.URLError, OSError, ValueError) as err:
        return str(getattr(err, "reason", err))


def check_file(path, root, external, timeout, cache, anchors_of):
    """Return a list of (line, target, problem) for one markdown file."""
    problems = []
    anchors, links = scan(path.read_text(encoding="utf-8", errors="replace"))
    anchors_of[path.resolve()] = anchors
    for number, target in links:
        if target.startswith("[") and target.endswith("]"):
            problems.append((number, target, "undefined reference link"))
        elif target.startswith(("http://", "https://")):
            if external:
                if target not in cache:
                    cache[target] = check_web(target, timeout)
                if cache[target]:
                    problems.append((number, target, cache[target]))
        elif target.lower().startswith(SKIP_SCHEMES):
            continue
        else:
            where, _, fragment = target.partition("#")
            if not where:
                destination = path.resolve()
            else:
                base = root if where.startswith("/") else path.parent
                destination = (base / where.lstrip("/")).resolve()
                if not destination.exists():
                    problems.append((number, target, "file not found"))
                    continue
            if fragment and destination.suffix.lower() in (".md", ".markdown"):
                if destination not in anchors_of:
                    anchors_of[destination] = scan(
                        destination.read_text(encoding="utf-8", errors="replace"))[0]
                if fragment.lower() not in anchors_of[destination]:
                    problems.append((number, target, "no heading with that anchor"))
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check links in markdown files.")
    parser.add_argument("paths", nargs="+", type=Path, help="markdown files or folders")
    parser.add_argument("--external", action="store_true", help="also check web (http/https) links")
    parser.add_argument("--root", type=Path, default=Path("."),
                        help="what links starting with / point to (current folder)")
    parser.add_argument("--timeout", type=float, default=8, help="seconds per web request (8)")
    args = parser.parse_args(argv)

    files = []
    for path in args.paths:
        if path.is_dir():
            files += sorted(p for p in path.rglob("*") if p.suffix.lower() in (".md", ".markdown"))
        elif path.is_file():
            files.append(path)
        else:
            print(f"not found: {path}", file=sys.stderr)
    if not files:
        print("No markdown files found.", file=sys.stderr)
        return 1
    broken, checked, cache, anchors_of = 0, 0, {}, {}
    for path in files:
        problems = check_file(path, args.root.resolve(), args.external, args.timeout, cache,
                              anchors_of)
        checked += 1
        for number, target, problem in problems:
            print(f"{path}:{number}  BROKEN  {target}  ({problem})")
        broken += len(problems)
    note = "" if args.external else " Web links were not checked (use --external)."
    print(f"\nChecked {checked} file(s): {broken} broken link(s).{note}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
