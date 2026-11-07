"""Show the HTTP response headers for a URL (or a saved header dump) with plain-English notes."""
import argparse
import re
import sys
import urllib.error  # web-ok: the network is only used when you give a URL
import urllib.request
from pathlib import Path

USER_AGENT = "daily-automation-scripts/1.0 (header inspector)"


def parse_headers(text):
    """Return (status_line, [(name, value), ...]) from raw `curl -I` style text."""
    status, headers = "", []
    for line in text.replace("\r\n", "\n").splitlines():
        if not line.strip():
            if headers:
                break  # a blank line ends the first response
            continue
        if re.match(r"^HTTP/\S+\s+\d{3}", line):
            status, headers = line.strip(), []
        elif ":" in line:
            name, _, value = line.partition(":")
            headers.append((name.strip().lower(), value.strip()))
    return status, headers


def human_duration(seconds):
    for unit, size in (("day", 86400), ("hour", 3600), ("minute", 60)):
        if seconds >= size:
            count = seconds // size
            return f"{count} {unit}{'' if count == 1 else 's'}"
    return f"{seconds} second{'' if seconds == 1 else 's'}"


def human_size(num):
    size = float(num)
    for unit in ("bytes", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "bytes" else f"{size:.1f} {unit}"
        size /= 1024


def notes_for(headers):
    """A few plain-English observations about the response."""
    values = {}
    for name, value in headers:
        values.setdefault(name, []).append(value)
    first = {name: vals[0] for name, vals in values.items()}
    notes = []
    if "content-type" in first:
        size = first.get("content-length", "")
        extra = f" ({human_size(int(size))})" if size.isdigit() else ""
        notes.append(f"Content: {first['content-type'].split(';')[0]}{extra}")
    cache = first.get("cache-control", "")
    match = re.search(r"max-age=(\d+)", cache)
    if "no-store" in cache:
        notes.append("Caching: not stored (no-store)")
    elif match:
        notes.append(f"Caching: reusable for {human_duration(int(match.group(1)))}")
    elif cache:
        notes.append(f"Caching: {cache}")
    if "location" in first:
        notes.append(f"Redirects to: {first['location']}")
    if "server" in first:
        notes.append(f"Server software announced: {first['server']}")
    if "x-powered-by" in first:
        notes.append(f"Technology revealed by X-Powered-By: {first['x-powered-by']}")
    if values.get("set-cookie"):
        count = len(values["set-cookie"])
        notes.append(f"Sets {count} cookie{'' if count == 1 else 's'}")
    notes.append("HSTS is on" if "strict-transport-security" in first else "No HSTS header")
    return notes


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def fetch_headers(url, follow=False, timeout=15):
    """Return a raw header dump (status line plus headers) for the URL."""
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        response = opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as err:   # 3xx/4xx/5xx still carry useful headers
        response = err
    version = "HTTP/2" if getattr(response, "version", 11) == 20 else "HTTP/1.1"
    status = getattr(response, "status", None) or getattr(response, "code", 0)
    lines = [f"{version} {status} {getattr(response, 'reason', '')}".strip()]
    lines += [f"{name}: {value}" for name, value in response.headers.items()]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspect HTTP response headers.")
    parser.add_argument("source", help="a URL, or a saved header dump (e.g. from curl -I)")
    parser.add_argument("--follow", action="store_true", help="follow redirects (URLs only)")
    args = parser.parse_args(argv)

    path = Path(args.source)
    try:
        if "://" in args.source:
            raw = fetch_headers(args.source, args.follow)
        elif path.is_file():
            raw = path.read_text(encoding="utf-8", errors="replace")
        else:
            parser.error(f"not a URL or a file: {args.source}")
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"Couldn't get headers: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1

    status, headers = parse_headers(raw)
    if not headers:
        print("No headers found in that input.", file=sys.stderr)
        return 1
    print(status or "(no status line)")
    width = max(len(name) for name, _ in headers)
    for name, value in headers:
        print(f"  {name:<{width}}  {value}")
    print("\nNotes:")
    for note in notes_for(headers):
        print(f"  - {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
