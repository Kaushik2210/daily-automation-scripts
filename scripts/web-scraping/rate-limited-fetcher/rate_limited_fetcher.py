"""Fetch URLs politely: a request rate limit, retries with backoff, and respect for Retry-After."""
import argparse
import email.utils
import hashlib
import random
import re
import sys
import time
import urllib.error  # web-ok: the network is only used with --apply; the plan works offline
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

USER_AGENT = "daily-automation-scripts/1.0 (polite fetcher)"
RETRY_STATUSES = {408, 425, 429, 500, 502, 503, 504}


def read_urls(items):
    lines = []
    for item in items:
        path = Path(item)
        if "://" not in item and path.is_file():
            lines += path.read_text(encoding="utf-8").splitlines()
        else:
            lines.append(item)
    urls, bad, seen = [], [], set()
    for line in (ln.strip() for ln in lines):
        if not line or line.startswith("#"):
            continue
        if urlsplit(line).scheme.lower() not in ("http", "https") or " " in line:
            bad.append(line)
        elif line not in seen:
            seen.add(line)
            urls.append(line)
    return urls, bad


def parse_retry_after(value, now=None):
    """Seconds to wait from a Retry-After header (a number or an HTTP date), or None."""
    if not value:
        return None
    value = value.strip()
    if re.fullmatch(r"\d+(\.\d+)?", value):
        return float(value)
    try:
        when = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    now = now or datetime.now(UTC)
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return max(0.0, (when - now).total_seconds())


def backoff_delay(attempt, base=1.0, cap=30.0, jitter=0.2, rng=random):
    """Exponential backoff: base, 2*base, 4*base... capped, with +/- jitter to spread clients."""
    delay = min(cap, base * 2 ** attempt)
    return max(0.0, delay * (1 + rng.uniform(-jitter, jitter)))


def schedule(count, rate):
    """Start offsets (seconds) for `count` requests at `rate` requests per second."""
    return [round(i / rate, 3) for i in range(count)]


def file_name(url):
    parts = urlsplit(url)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", unquote(Path(parts.path).name)).strip(" .")
    suffix = "-" + hashlib.sha256(url.encode()).hexdigest()[:6]
    return (name + suffix) if (not name or parts.query or "." not in name) else name


def fetch_once(url, timeout):
    """One blocking request. Returns (status, headers dict, body bytes, error text)."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, dict(response.headers), response.read(5_000_000), ""
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers), b"", f"HTTP {err.code}"
    except (urllib.error.URLError, OSError, ValueError) as err:
        return 0, {}, b"", str(getattr(err, "reason", err))


def fetch_all(urls, rate, retries, timeout, backoff, fetch=fetch_once, sleep=time.sleep,
              clock=time.monotonic, rng=random, out=print):
    """Fetch every URL in order, keeping at least 1/rate seconds between requests to a host."""
    last_by_host, results = {}, []
    for url in urls:
        host = urlsplit(url).netloc.lower()
        for attempt in range(retries + 1):
            wait = last_by_host.get(host, -1e9) + 1 / rate - clock()
            if wait > 0:
                sleep(wait)
            last_by_host[host] = clock()
            status, headers, body, error = fetch(url, timeout)
            retry = status in RETRY_STATUSES or status == 0
            if not retry or attempt == retries:
                break
            asked = parse_retry_after({k.lower(): v for k, v in headers.items()}.get("retry-after"))
            delay = asked if asked is not None else backoff_delay(attempt, backoff, rng=rng)
            out(f"  {url}: {status or error or 'no answer'}; retry {attempt + 1}/{retries} in "
                f"{delay:.1f}s" + (" (server asked)" if asked is not None else ""))
            sleep(delay)
        results.append({"url": url, "status": status, "bytes": len(body), "error": error,
                        "body": body, "attempts": attempt + 1})
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fetch URLs politely with rate limits.")
    parser.add_argument("urls", nargs="+", help="URLs or text files with one URL per line")
    parser.add_argument("--rate", type=float, default=1.0, help="requests per second per site (1)")
    parser.add_argument("--retries", type=int, default=3, help="retries after 429/5xx/errors (3)")
    parser.add_argument("--backoff", type=float, default=1.0, help="first retry pause, seconds (1)")
    parser.add_argument("--timeout", type=float, default=15, help="seconds per request (15)")
    parser.add_argument("-o", "--outdir", type=Path, help="also save each response body here")
    parser.add_argument("--apply", action="store_true",
                        help="really make the requests (default only shows the plan)")
    args = parser.parse_args(argv)
    if args.rate <= 0 or args.retries < 0 or args.backoff < 0:
        parser.error("--rate must be above 0; --retries and --backoff can't be negative")

    urls, bad = read_urls(args.urls)
    if not urls:
        print("No valid http(s) URLs given.", file=sys.stderr)
        return 1
    by_host = {}
    for url in urls:
        by_host.setdefault(urlsplit(url).netloc.lower(), []).append(url)
    hosts = by_host
    print(f"{len(urls)} URL(s) on {len(hosts)} site(s), {args.rate:g} request(s)/second per site, "
          f"up to {args.retries} retries ({len(bad)} invalid skipped)")
    if not args.apply:
        when = {}
        for host_urls in by_host.values():
            when.update(zip(host_urls, schedule(len(host_urls), args.rate), strict=True))
        for url in urls:
            print(f"  t+{when[url]:5.1f}s  {url}")
        slowest = max(when.values())
        print(f"\nPlan only: about {slowest:.1f}s without retries (retries wait "
              f"{args.backoff:g}s, {args.backoff * 2:g}s, {args.backoff * 4:g}s... or the "
              "server's Retry-After). Use --apply to fetch.")
        return 0

    results = fetch_all(urls, args.rate, args.retries, args.timeout, args.backoff)
    failed = 0
    for item in results:
        ok = 200 <= item["status"] < 400
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {item['status'] or '---':>3} {item['bytes']:>8} B "
              f"{item['attempts']} try  {item['url']}" + (f"  ({item['error']})" if item["error"]
                                                          else ""))
        if args.outdir and ok:
            args.outdir.mkdir(parents=True, exist_ok=True)
            target = args.outdir / file_name(item["url"])
            if not target.exists():
                target.write_bytes(item["body"])
    print(f"\n{len(results) - failed} fetched, {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
