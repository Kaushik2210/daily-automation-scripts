"""Benchmark an endpoint's latency with percentiles (p50, p90, p95, p99) or summarise timings."""
import argparse
import csv
import statistics
import sys
import time
import urllib.error  # web-ok: the network is only used when benchmarking; --summarise works offline
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

USER_AGENT = "daily-automation-scripts/1.0 (latency benchmark)"
MAX_REQUESTS, MAX_CONCURRENCY = 5000, 100


def percentile(sorted_values, p):
    """The p-th percentile (0-100) with linear interpolation between neighbours."""
    if not sorted_values:
        raise ValueError("no values")
    position = (len(sorted_values) - 1) * p / 100
    low = int(position)
    high = min(low + 1, len(sorted_values) - 1)
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * (position - low)


def summarise(times):
    """Statistics for a list of latencies in milliseconds."""
    ordered = sorted(times)
    return {"count": len(ordered), "min": ordered[0], "mean": statistics.fmean(ordered),
            "median": percentile(ordered, 50), "p90": percentile(ordered, 90),
            "p95": percentile(ordered, 95), "p99": percentile(ordered, 99), "max": ordered[-1],
            "stdev": statistics.stdev(ordered) if len(ordered) > 1 else 0.0}


def histogram(times, bins=8):
    """[(low, high, count)] with equal-width bins."""
    low, high = min(times), max(times)
    if low == high:
        return [(low, high, len(times))]
    width = (high - low) / bins
    counts = [0] * bins
    for value in times:
        counts[min(int((value - low) / width), bins - 1)] += 1
    return [(low + i * width, low + (i + 1) * width, c) for i, c in enumerate(counts)]


def request_once(url, method, timeout):
    """One request. Returns (milliseconds, status, error)."""
    request = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read(1_000_000)
            status, error = response.status, ""
    except urllib.error.HTTPError as err:
        status, error = err.code, f"HTTP {err.code}"
    except (urllib.error.URLError, OSError, ValueError) as err:
        status, error = 0, str(getattr(err, "reason", err))
    return (time.perf_counter() - started) * 1000, status, error


def benchmark(url, count, concurrency, warmup, method, timeout, call=request_once):
    """Run the benchmark. Returns (results list of (ms, status, error), wall seconds)."""
    for _ in range(warmup):
        call(url, method, timeout)
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(lambda _: call(url, method, timeout), range(count)))
    return results, time.perf_counter() - started


def read_timings(path):
    """Latencies from a text file (one number per line) or a CSV with an 'ms' column."""
    text = path.read_text(encoding="utf-8")
    first = text.lstrip().splitlines()[0] if text.strip() else ""
    if "," in first and not first.replace(",", "").replace(".", "").strip().isdigit():
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        column = next((c for c in rows[0] if c.lower() in ("ms", "latency_ms", "time_ms")), None)
        if column is None:
            raise ValueError("the CSV needs an 'ms' column")
        return [float(r[column]) for r in rows if r[column].strip()]
    return [float(line) for line in text.split() if line.strip()]


def show(times, slow_ms):
    stats = summarise(times)
    print(f"{stats['count']} sample(s), ms:  min {stats['min']:.1f}  mean {stats['mean']:.1f}  "
          f"median {stats['median']:.1f}  stdev {stats['stdev']:.1f}  max {stats['max']:.1f}")
    print(f"percentiles:  p90 {stats['p90']:.1f}  p95 {stats['p95']:.1f}  p99 {stats['p99']:.1f}")
    bins = histogram(times)
    peak = max(c for _, _, c in bins)
    print("\nDistribution (ms):")
    for low, high, count in bins:
        bar = "#" * (max(1, round(40 * count / peak)) if count else 0)
        print(f"  {low:8.1f} - {high:8.1f}  {bar:<40} {count}")
    slow = sum(t > slow_ms for t in times)
    if slow:
        print(f"\n{slow} sample(s) slower than {slow_ms:g} ms.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Benchmark endpoint latency with percentiles.")
    parser.add_argument("url", nargs="?", help="the endpoint to benchmark (your own server!)")
    parser.add_argument("-n", "--requests", type=int, default=100,
                        help=f"number of requests, up to {MAX_REQUESTS} (100)")
    parser.add_argument("-c", "--concurrency", type=int, default=5,
                        help=f"requests at once, up to {MAX_CONCURRENCY} (5)")
    parser.add_argument("--warmup", type=int, default=3, help="requests not counted first (3)")
    parser.add_argument("--method", choices=["GET", "HEAD"], default="GET")
    parser.add_argument("--timeout", type=float, default=10, help="seconds per request (10)")
    parser.add_argument("--slow", type=float, default=1000, help="ms that count as slow (1000)")
    parser.add_argument("--csv", type=Path, help="save every measurement to this new CSV file")
    parser.add_argument("--summarise", type=Path,
                        help="summarise saved timings (one number per line, or a CSV with 'ms')")
    args = parser.parse_args(argv)

    if args.summarise:
        if not args.summarise.is_file():
            parser.error(f"not a file: {args.summarise}")
        try:
            times = read_timings(args.summarise)
        except (OSError, ValueError) as err:
            print(f"Can't read the timings: {err}", file=sys.stderr)
            return 1
        if not times:
            print("No timings found.", file=sys.stderr)
            return 1
        show(times, args.slow)
        return 0
    if not args.url or not args.url.startswith(("http://", "https://")):
        parser.error("give an http(s) URL to benchmark, or --summarise FILE")
    if not 1 <= args.requests <= MAX_REQUESTS or not 1 <= args.concurrency <= MAX_CONCURRENCY:
        parser.error(f"--requests must be 1-{MAX_REQUESTS} and --concurrency 1-{MAX_CONCURRENCY}")
    if args.csv and args.csv.exists():
        parser.error(f"{args.csv} already exists; choose another name")

    print(f"{args.method} {args.url}: {args.requests} request(s), {args.concurrency} at a time, "
          f"{args.warmup} warm-up (only benchmark servers you own or may test)")
    results, wall = benchmark(args.url, args.requests, args.concurrency, args.warmup,
                              args.method, args.timeout)
    good = [ms for ms, status, error in results if 0 < status < 500 and not error]
    errors = [(status, error) for _, status, error in results if not (0 < status < 400) or error]
    statuses = {}
    for _, status, _ in results:
        statuses[status] = statuses.get(status, 0) + 1
    summary = ", ".join(f"{s or 'no answer'} x{n}" for s, n in sorted(statuses.items()))
    print(f"status codes: {summary}")
    print(f"throughput: {len(results) / wall:.1f} requests/second over {wall:.2f}s\n")
    if args.csv:
        with args.csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(["ms", "status", "error"])
            writer.writerows([f"{ms:.2f}", status, error] for ms, status, error in results)
        print(f"Saved {args.csv}\n")
    if good:
        show(good, args.slow)
    else:
        print("No successful responses to summarise.")
    if errors:
        example = errors[0][1] or errors[0][0]
        print(f"\n{len(errors)} request(s) failed or returned errors (e.g. {example}).")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
