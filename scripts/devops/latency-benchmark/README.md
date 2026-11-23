# latency-benchmark

## Purpose
Measure how fast an endpoint really responds. The tool sends a number of requests (a few at a time or in parallel), times each one and reports the **minimum, mean, median, standard deviation, maximum and the p90, p95 and p99 percentiles** (p95 = 95% of requests were faster than this), plus the throughput in requests per second, the status codes seen and a text histogram showing the shape of the distribution. Percentiles matter more than the average: a few slow requests can hide behind a good mean.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python latency_benchmark.py URL [-n 100] [-c 5] [--warmup 3] [--method GET|HEAD] [--timeout 10] [--csv raw.csv]
python latency_benchmark.py --summarise timings.txt [--slow 1000]
```
The warm-up requests aren't counted (they let connections and caches settle). `--csv` saves every measurement to a new file (never overwriting). `--summarise` analyses saved timings, either one number per line or a CSV with an `ms` column such as the one `--csv` writes. Requests are limited to 5000 and concurrency to 100. The exit code is 1 if any request failed or returned an error. **Only benchmark servers you own or have permission to test**: this tool can generate real load.

## Example
```bash
python latency_benchmark.py --summarise latencies.txt --slow 500
```
```
50 sample(s), ms:  min 79.0  mean 116.4  median 86.5  stdev 162.7  max 1210.0
percentiles:  p90 93.1  p95 158.2  p99 783.7

Distribution (ms):
      79.0 -    220.4  ######################################## 48
     220.4 -    361.8  #                                        1
     361.8 -    503.1                                           0
     503.1 -    644.5                                           0
     644.5 -    785.9                                           0
     785.9 -    927.2                                           0
     927.2 -   1068.6                                           0
    1068.6 -   1210.0  #                                        1

1 sample(s) slower than 500 ms.
```

## Notes
- Timings include connection setup (a fresh connection per request), so they are a bit higher than a browser reusing connections.
- Run it from a machine close to the server if you want to measure the server rather than the network.
- Use `health-check-poller` for repeated uptime checks and `api-smoke-tester` to verify responses.
- The website demo summarises saved timings; benchmarking a live endpoint works on your own computer.
