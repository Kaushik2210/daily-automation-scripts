# job-listing-watcher

## Purpose
Be first to know about a new opening. The tool reads a company's careers page, picks out the links that look like job postings, remembers them, and on every later run tells you which postings are new and which have closed. Use `--match` to care only about the roles you want. The exit code is 1 when something new appeared, so cron or Task Scheduler can notify you.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python job_listing_watcher.py SOURCE --state seen-jobs.json [--match "engineer|data"] [--base URL]
python job_listing_watcher.py SOURCE --previous earlier-copy.html
```
A link counts as a posting when its address contains words like `job`, `career`, `position` or `opening`; change that with `--link-pattern`. With `--state` the first run saves a baseline. `--previous` compares against a saved page and writes nothing.

## Example
```bash
python job_listing_watcher.py jobs.html --previous jobs-old.html --base https://acme.test/
```
```
NEW     Product Designer  <https://acme.test/jobs/102-designer>
  NEW     Data Analyst  <https://acme.test/jobs/103-data-analyst>
  CLOSED  Summer Intern
2 new, 1 closed, 1 unchanged.
```

## Notes
- Links are matched on their address and need some visible text; image-only links are skipped.
- Careers pages built with JavaScript often don't list jobs in the raw HTML. Save the rendered page, or look for the company's job-board address and watch that instead.
- Check a few times a day at most; there is no rush that justifies hammering a website.
- The website demo only compares saved files; watching a URL works on your own computer.
