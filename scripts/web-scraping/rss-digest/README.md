# rss-digest

## Purpose
Skim your feeds without opening a reader. It reads RSS and Atom feeds, picks the newest items from each, tidies the summaries (no HTML) and writes a short markdown digest you can read, paste into notes or email to yourself.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python rss_digest.py FEED [FEED ...] [--since YYYY-MM-DD] [--limit N] [-o digest.md --apply]
```
`FEED` is a feed URL or a saved feed file. By default it shows the 5 newest items per feed. The digest is printed; to save it pass `-o` with `--apply` (an existing file is never overwritten).

## Example
```bash
python rss_digest.py feed.xml --since 2026-01-01 --limit 3
```
```
# Feed digest (3 item(s) from 1 feed(s))

## ACME Blog

- **Launching widgets 2.0** (2026-01-13) - Faster, lighter and cheaper than ever. [read](https://example.com/blog/widgets-2)
- **How we test our widgets** (2026-01-12) - A look inside the lab. [read](https://example.com/blog/testing)
- **Holiday opening hours** (2026-01-02) - We are closed on public holidays. [read](https://example.com/blog/holidays)
```

## Notes
- Downloading a feed needs network access; the website demo uses a sample feed file.
- Feeds that contain a DOCTYPE or entity definitions are refused, which protects against malicious XML.
- Items with no date are listed after dated ones and are left out when you use `--since`.
