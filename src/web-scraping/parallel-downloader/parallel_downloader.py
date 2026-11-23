"""Download many files in parallel, resuming partial downloads and never overwriting files."""
import argparse
import hashlib
import re
import sys
import time
import urllib.error  # web-ok: the network is only used with --apply; the plan works offline
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import unquote, urlsplit

USER_AGENT = "daily-automation-scripts/1.0 (parallel downloader)"
CHUNK = 64 * 1024


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


def file_name(url):
    """A safe local name from the URL path, or a short hash when the path has none."""
    parts = urlsplit(url)
    name = unquote(Path(parts.path).name)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    if not name:
        name = "download-" + hashlib.sha256(url.encode()).hexdigest()[:8]
    elif parts.query and "." not in name:
        name += "-" + hashlib.sha256(parts.query.encode()).hexdigest()[:6]
    return name


def unique_names(urls):
    """Map each URL to a distinct file name (a second 'a.pdf' becomes 'a (1).pdf')."""
    taken, names = set(), {}
    for url in urls:
        base = Path(file_name(url))
        name, number = base.name, 1
        while name.lower() in taken:
            name = f"{base.stem} ({number}){base.suffix}"
            number += 1
        taken.add(name.lower())
        names[url] = name
    return names


def state_of(outdir, name):
    """('done', 0) when the file exists, ('resume', bytes) when a .part file exists, else new."""
    if (outdir / name).exists():
        return "done", 0
    part = outdir / f"{name}.part"
    if part.exists() and part.stat().st_size > 0:
        return "resume", part.stat().st_size
    return "new", 0


def download(url, outdir, name, timeout, retries):
    """Fetch one file, resuming from a .part file. Returns (bytes in the file, resumed?)."""
    part, final = outdir / f"{name}.part", outdir / name
    resumed = False
    for attempt in range(retries + 1):
        have = part.stat().st_size if part.exists() else 0
        headers = {"User-Agent": USER_AGENT}
        if have:
            headers["Range"] = f"bytes={have}-"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers),
                                        timeout=timeout) as response:
                partial = response.status == 206
                if have and not partial:
                    have = 0  # the server ignored Range: start the file again
                resumed = resumed or (partial and have > 0)
                with part.open("ab" if partial else "wb") as handle:
                    while chunk := response.read(CHUNK):
                        handle.write(chunk)
                expected = response.headers.get("Content-Length")
            size = part.stat().st_size
            total = have + int(expected) if expected and expected.isdigit() else None
            if total is not None and size != total:
                raise OSError(f"incomplete download ({size} of {total} bytes)")
            if final.exists():
                raise OSError(f"{name} appeared while downloading; kept {part.name}")
            part.replace(final)
            return size, resumed
        except urllib.error.HTTPError as err:
            if err.code == 416 and part.exists():  # asked beyond the end: it was already complete
                part.replace(final)
                return final.stat().st_size, True
            if err.code < 500 or attempt == retries:
                raise OSError(f"HTTP {err.code}") from None
        except (urllib.error.URLError, OSError, TimeoutError) as err:
            if attempt == retries:
                raise OSError(str(getattr(err, "reason", err))) from None
        time.sleep(0.3 * 2 ** attempt)
    raise OSError("download failed")


def human(size):
    for unit in ("B", "KB", "MB"):
        if size < 1024:
            return f"{size:.0f} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Download many files in parallel, with resume.")
    parser.add_argument("urls", nargs="+", help="URLs or text files with one URL per line")
    parser.add_argument("-o", "--outdir", type=Path, default=Path("downloads"),
                        help="folder for the files (downloads)")
    parser.add_argument("--workers", type=int, default=4, help="downloads at once (4)")
    parser.add_argument("--timeout", type=float, default=30, help="seconds without data (30)")
    parser.add_argument("--retries", type=int, default=2, help="retries per file, resuming (2)")
    parser.add_argument("--apply", action="store_true",
                        help="really download (default only shows the plan)")
    args = parser.parse_args(argv)
    if args.workers < 1 or args.retries < 0:
        parser.error("--workers must be at least 1")

    urls, bad = read_urls(args.urls)
    if not urls:
        print("No valid http(s) URLs given.", file=sys.stderr)
        return 1
    names = unique_names(urls)
    todo = []
    print(f"{len(urls)} file(s) to {args.outdir}/ ({len(bad)} invalid line(s) skipped)")
    for url in urls:
        status, have = state_of(args.outdir, names[url])
        label = {"done": "exists, skipped", "resume": f"resume from {human(have)}",
                 "new": "new"}[status]
        print(f"  {names[url]:<34} {label:<22} {url}")
        if status != "done":
            todo.append(url)
    for line in bad[:3]:
        print(f"  skipping invalid: {line}")
    if not args.apply:
        print(f"\nDry run: {len(todo)} to download with {args.workers} at once. "
              "Use --apply to start.")
        return 0
    if not todo:
        print("\nNothing to download.")
        return 0

    args.outdir.mkdir(parents=True, exist_ok=True)
    failures = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs = {pool.submit(download, u, args.outdir, names[u], args.timeout, args.retries): u
                for u in todo}
        for job in as_completed(jobs):
            url = jobs[job]
            try:
                size, resumed = job.result()
                print(f"done  {names[url]} ({human(size)}{', resumed' if resumed else ''})")
            except OSError as err:
                failures += 1
                print(f"FAIL  {names[url]}: {err}")
    print(f"\n{len(todo) - failures} downloaded, {failures} failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
