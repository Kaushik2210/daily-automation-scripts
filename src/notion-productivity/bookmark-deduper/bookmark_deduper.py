"""Remove duplicate bookmarks from a browser HTML export. Dry run by default."""
import argparse
import html
import re
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit

LINK = re.compile(r"""<A\s[^>]*?HREF\s*=\s*["']([^"']*)["'][^>]*>(.*?)</A>""",
                  re.IGNORECASE | re.DOTALL)
TRACKING = ("utm_", "fbclid", "gclid", "mc_cid", "mc_eid", "igshid", "ref_src")
DEFAULT_PORTS = {"http": 80, "https": 443}


def normalise(url):
    """A form of the address that is the same for links which point to the same page."""
    parts = urlsplit(html.unescape(url.strip()))
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        return url.strip()  # mailto:, javascript:, place: and friends compare as written
    host = parts.hostname.lower().removeprefix("www.")
    usual = DEFAULT_PORTS[parts.scheme.lower()]
    port = f":{parts.port}" if parts.port and parts.port != usual else ""
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                       if not k.lower().startswith(TRACKING)])
    return f"{host}{port}{parts.path.rstrip('/') or ''}" + (f"?{query}" if query else "")


def find_duplicates(text):
    """Return (kept, removed, lines to drop). Each entry is (line number, title, url)."""
    lines = text.splitlines()
    seen, kept, removed, drop = {}, [], [], set()
    for number, line in enumerate(lines):
        match = LINK.search(line)
        if not match:
            continue
        url, title = match.group(1), re.sub(r"<[^>]+>", "", match.group(2)).strip()
        key = normalise(url)
        entry = (number + 1, html.unescape(title), url)
        if key in seen:
            removed.append((entry, seen[key]))
            drop.add(number)
            nxt = number + 1  # a <DD> description line belongs to the bookmark above it
            while nxt < len(lines) and lines[nxt].lstrip().upper().startswith("<DD>"):
                drop.add(nxt)
                nxt += 1
        else:
            seen[key] = entry
            kept.append(entry)
    return kept, removed, drop


def clean_text(text, drop):
    lines = text.splitlines()
    return "\n".join(line for number, line in enumerate(lines) if number not in drop) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Remove duplicate bookmarks from an HTML export.")
    parser.add_argument("export", type=Path, help="bookmarks HTML file exported from your browser")
    parser.add_argument("--out", type=Path, help="new file to write the cleaned bookmarks to")
    parser.add_argument("--apply", action="store_true", help="actually write the cleaned file")
    args = parser.parse_args(argv)
    if args.apply and not args.out:
        parser.error("--apply needs --out FILE (the original is never changed)")
    if not args.export.is_file():
        parser.error(f"not a file: {args.export}")
    if args.out and args.apply and args.out.exists():
        print(f"{args.out} already exists - pick a new name so nothing is overwritten.")
        return 1

    text = args.export.read_text(encoding="utf-8-sig", errors="replace")
    kept, removed, drop = find_duplicates(text)
    if not kept and not removed:
        print("No bookmarks found in that file.")
        return 1
    print(f"{len(kept) + len(removed)} bookmark(s): {len(kept)} unique, "
          f"{len(removed)} duplicate(s).")
    for (number, title, url), (first_number, first_title, _first_url) in removed:
        print(f"  duplicate (line {number}) {title or url}\n"
              f"    same page as line {first_number}: {first_title or 'untitled'}")
    if not removed:
        return 0
    if not args.apply:
        print("\nDry run - nothing written. Add --out FILE --apply to save a cleaned copy.")
        return 0
    args.out.write_text(clean_text(text, drop), encoding="utf-8")
    print(f"\nWrote {args.out} without the duplicates. Folders left empty are kept as they were.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
