"""Check the HTTP status of many URLs at once: working, redirecting or broken."""
import argparse
import sys
import time
import urllib.error  # web-ok: the network is only used when you don't pass --plan
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

USER_AGENT = "daily-automation-scripts/1.0 (url checker)"


def normalize(url):
    """Lowercase the host, drop the #fragment and treat '' and '/' paths as the same page."""
    parts = urlsplit(url.strip())
    path = parts.path or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def is_http_url(text):
    text = text.strip()
    parts = urlsplit(text)
    return parts.scheme.lower() in ("http", "https") and bool(parts.netloc) and " " not in text


def read_inputs(items):
    """Each item is a URL, or the path of a text file holding one URL per line (# = comment)."""
    lines = []
    for item in items:
        path = Path(item)
        if "://" not in item and path.is_file():
            lines.extend(path.read_text(encoding="utf-8").splitlines())
        else:
            lines.append(item)
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def plan(lines):
    """Split into (urls_to_check, invalid_lines, duplicate_count), keeping first-seen order."""
    seen, urls, invalid, dupes = set(), [], [], 0
    for line in lines:
        if not is_http_url(line):
            invalid.append(line)
            continue
        url = normalize(line)
        if url in seen:
            dupes += 1
        else:
            seen.add(url)
            urls.append(url)
    return urls, invalid, dupes


def check_url(url, timeout=10):
    """Return {'url','status','final','ms','error'}; tries HEAD first, then GET if refused."""
    started = time.monotonic()
    result = {"url": url, "status": None, "final": url, "ms": 0, "error": None}
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result.update(status=response.status, final=response.geturl())
                break
        except urllib.error.HTTPError as err:
            if method == "HEAD" and err.code in (403, 405, 501):
                continue
            result.update(status=err.code, final=err.geturl() or url)
            break
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as err:
            result["error"] = str(getattr(err, "reason", err))
            break
    result["ms"] = round((time.monotonic() - started) * 1000)
    return result


def is_ok(result):
    return result["status"] is not None and result["status"] < 400


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check the status of many URLs.")
    parser.add_argument("urls", nargs="+", help="URLs, or text files with one URL per line")
    parser.add_argument("--plan", action="store_true",
                        help="only list what would be checked (no requests are made)")
    parser.add_argument("--timeout", type=float, default=10, help="seconds per request (10)")
    parser.add_argument("--workers", type=int, default=8, help="requests at the same time (8)")
    args = parser.parse_args(argv)

    urls, invalid, dupes = plan(read_inputs(args.urls))
    for line in invalid:
        print(f"SKIP  not an http(s) URL: {line}")
    if args.plan:
        for url in urls:
            print(f"WOULD CHECK  {url}")
        print(f"Would check {len(urls)} URL(s); {len(invalid)} invalid, "
              f"{dupes} duplicate(s) removed.")
        return 0
    if not urls:
        print("No valid URLs to check.")
        return 1
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        results = list(pool.map(lambda u: check_url(u, args.timeout), urls))
    for r in results:
        label = "OK  " if is_ok(r) else "FAIL"
        detail = r["status"] or r["error"]
        moved = f"  -> {r['final']}" if r["final"] != r["url"] else ""
        print(f"{label} {str(detail):<22} {r['ms']:>5} ms  {r['url']}{moved}")
    broken = sum(not is_ok(r) for r in results)
    print(f"{len(results)} checked, {len(results) - broken} ok, {broken} broken.")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
