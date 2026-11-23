"""Check thousands of URLs concurrently (asyncio) with global and per-host limits."""
import argparse
import asyncio
import csv
import sys
import time
import urllib.error  # web-ok: the network is only used when checking; --plan and --summarise don't
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit

USER_AGENT = "daily-automation-scripts/1.0 (async url checker)"
FIELDS = ["url", "status", "ms", "final_url", "error"]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def is_http_url(text):
    parts = urlsplit(text.strip())
    return parts.scheme.lower() in ("http", "https") and bool(parts.netloc) and " " not in text


def read_urls(items):
    """Return (unique valid URLs in order, invalid lines, number of duplicates)."""
    lines = []
    for item in items:
        path = Path(item)
        if "://" not in item and path.is_file():
            lines += path.read_text(encoding="utf-8").splitlines()
        else:
            lines.append(item)
    urls, invalid, seen, duplicates = [], [], set(), 0
    for line in (ln.strip() for ln in lines):
        if not line or line.startswith("#"):
            continue
        if not is_http_url(line):
            invalid.append(line)
        elif line in seen:
            duplicates += 1
        else:
            seen.add(line)
            urls.append(line)
    return urls, invalid, duplicates


def request_once(url, timeout, method, follow):
    """One blocking request. Returns (status, final_url, error)."""
    opener = urllib.request.build_opener(*([] if follow else [NoRedirect]))
    req = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
    try:
        with opener.open(req, timeout=timeout) as response:
            return response.status, response.geturl(), ""
    except urllib.error.HTTPError as err:
        return err.code, url, f"HTTP {err.code}" if err.code >= 400 else ""
    except (urllib.error.URLError, OSError, ValueError) as err:
        return 0, "", str(getattr(err, "reason", err)) or err.__class__.__name__


async def check_url(url, limits, timeout, retries, method, follow):
    """Check one URL, holding a global slot and a slot for its host."""
    host = urlsplit(url).netloc.lower()
    host_slot = limits["hosts"].setdefault(host, asyncio.Semaphore(limits["per_host"]))
    async with limits["all"], host_slot:
        started = time.perf_counter()
        status, final, error = 0, "", ""
        for attempt in range(retries + 1):
            status, final, error = await asyncio.to_thread(request_once, url, timeout, method,
                                                           follow)
            if method == "HEAD" and status in (405, 501):  # some servers refuse HEAD
                status, final, error = await asyncio.to_thread(request_once, url, timeout, "GET",
                                                               follow)
            if 0 < status < 500 or attempt == retries:
                break
            await asyncio.sleep(0.2 * 2 ** attempt)  # brief backoff for 5xx and network errors
        ms = round((time.perf_counter() - started) * 1000) if status else ""
        return {"url": url, "status": status, "ms": ms, "final_url": final, "error": error}


async def check_all(urls, concurrency, per_host, timeout, retries, method, follow, progress=None):
    limits = {"all": asyncio.Semaphore(concurrency), "hosts": {}, "per_host": per_host}
    loop = asyncio.get_running_loop()
    loop.set_default_executor(ThreadPoolExecutor(max_workers=concurrency))
    results = {}
    tasks = [asyncio.create_task(check_url(u, limits, timeout, retries, method, follow))
             for u in urls]
    for done, finished in enumerate(asyncio.as_completed(tasks), 1):
        result = await finished
        results[result["url"]] = result
        if progress:
            progress(done, len(urls))
    return [results[u] for u in urls]


def classify(row):
    status = int(row["status"] or 0)
    if status == 0:
        return "failed"
    if status >= 500:
        return "server error"
    if status >= 400:
        return "client error"
    if status >= 300 or (row.get("final_url") and row["final_url"] != row["url"]):
        return "redirect"
    return "ok"


def read_results(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if row.get("url")]


def report(rows, slow_ms, only_problems):
    groups = {}
    for row in rows:
        groups.setdefault(classify(row), []).append(row)
    for row in rows:
        kind = classify(row)
        slow = str(row["ms"]).isdigit() and int(row["ms"]) > slow_ms
        if only_problems and kind in ("ok", "redirect") and not slow:
            continue
        detail = row["error"] or (f"-> {row['final_url']}" if kind == "redirect" else "")
        ms = f"{row['ms']} ms" if row["ms"] != "" else "---"
        print(f"{kind.upper():<13} {row['status'] or '---':>3} {ms:>8}  {row['url']}  {detail}"
              + ("  (slow)" if slow else ""))
    counts = ", ".join(f"{len(groups[k])} {k}" for k in
                       ("ok", "redirect", "client error", "server error", "failed") if k in groups)
    times = sorted(int(r["ms"]) for r in rows if str(r["ms"]).isdigit())
    print(f"\n{len(rows)} URL(s): {counts}.")
    if times:
        print(f"Response times: median {times[len(times) // 2]} ms, slowest {times[-1]} ms.")
    return sum(len(v) for k, v in groups.items() if k not in ("ok", "redirect"))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check many URLs concurrently.")
    parser.add_argument("urls", nargs="*", help="URLs or text files with one URL per line")
    parser.add_argument("--concurrency", type=int, default=50, help="requests at once (50)")
    parser.add_argument("--per-host", type=int, default=5, help="requests at once per site (5)")
    parser.add_argument("--timeout", type=float, default=10, help="seconds per request (10)")
    parser.add_argument("--retries", type=int, default=1, help="retries after 5xx or errors (1)")
    parser.add_argument("--method", choices=["HEAD", "GET"], default="HEAD")
    parser.add_argument("--no-follow", action="store_true", help="report redirects, don't follow")
    parser.add_argument("--slow", type=int, default=2000, help="ms that count as slow (2000)")
    parser.add_argument("--only-problems", action="store_true", help="hide the working URLs")
    parser.add_argument("--csv", type=Path, help="save the results to this new CSV file")
    parser.add_argument("--summarise", type=Path, help="report on a saved CSV instead of checking")
    parser.add_argument("--plan", action="store_true", help="validate the list; make no requests")
    args = parser.parse_args(argv)
    if not args.urls and not args.summarise:
        parser.error("give URLs or files of URLs, or --summarise RESULTS.csv")
    if min(args.concurrency, args.per_host) < 1 or args.retries < 0:
        parser.error("--concurrency and --per-host must be at least 1")

    if args.summarise:
        if not args.summarise.is_file():
            parser.error(f"not a file: {args.summarise}")
        rows = read_results(args.summarise)
        return 1 if report(rows, args.slow, args.only_problems) else 0

    urls, invalid, duplicates = read_urls(args.urls)
    hosts = {urlsplit(u).netloc.lower() for u in urls}
    print(f"{len(urls)} URL(s) on {len(hosts)} site(s); {duplicates} duplicate(s) removed, "
          f"{len(invalid)} invalid.")
    for line in invalid[:5]:
        print(f"  skipping: {line}")
    if args.plan or not urls:
        waves = -(-len(urls) // args.concurrency)
        print(f"Plan: {args.concurrency} at a time ({args.per_host} per site) = about {waves} "
              f"wave(s). No requests were made.")
        return 0 if urls else 1
    if args.csv and args.csv.exists():
        parser.error(f"{args.csv} already exists; choose another name")

    def progress(done, total):
        if total >= 50 and done % 25 == 0:
            print(f"  ... {done}/{total}", file=sys.stderr)

    rows = asyncio.run(check_all(urls, args.concurrency, args.per_host, args.timeout, args.retries,
                                 args.method, not args.no_follow, progress))
    problems = report(rows, args.slow, args.only_problems)
    if args.csv:
        with args.csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        print(f"Saved {args.csv}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
