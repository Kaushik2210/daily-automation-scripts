# parallel-downloader

## Purpose
Download a list of files several at a time, and pick up where an interrupted download left off. Files are saved as `NAME.part` while they download and renamed to `NAME` only when complete, so you never end up with a half-finished file that looks finished. If a `.part` file exists from an earlier run, the tool asks the server to continue from that point (an HTTP `Range` request); if the server can't resume, it starts that file again cleanly. Files that already exist are never overwritten, and two URLs with the same file name get `(1)`, `(2)`... added.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python parallel_downloader.py file-urls.txt [https://more.example/a.zip] [-o downloads] [--workers 4]
                              [--timeout 30] [--retries 2] [--apply]
```
URLs can be given directly or in text files with one per line (`#` starts a comment). **Dry run by default:** it prints each file's name and state (`new`, `resume from 2.0 KB`, `exists, skipped`) without touching the network. Add `--apply` to download with `--workers` at a time. Each failed file is retried (resuming) up to `--retries` times, and the final line counts what succeeded and failed; the exit code is 1 if anything failed. Only download files you have the right to download.

## Example
```bash
python parallel_downloader.py file-urls.txt -o dl
```
```
4 file(s) to dl/ (1 invalid line(s) skipped)
  report-q3.pdf                      resume from 2.0 KB     https://downloads.example.com/reports/report-q3.pdf
  logo.png                           exists, skipped        https://downloads.example.com/images/logo.png
  export-2026-11.csv                 new                    https://downloads.example.com/data/export-2026-11.csv
  archive-ef9a75                     new                    https://downloads.example.com/archive?id=77&format=zip
  skipping invalid: ftp://files.example.com/old.iso

Dry run: 3 to download with 4 at once. Use --apply to start.
```

## Notes
- File names come from the URL path (`q3%20report.pdf` becomes `q3 report.pdf`); a URL with no usable name gets a short hash name.
- When the server reports the file size, the finished download is checked against it.
- Use `image-downloader` to grab pictures from a page and `rate-limited-fetcher` when you need to be gentler with a server.
- The website demo shows the plan; downloading works on your own computer.
