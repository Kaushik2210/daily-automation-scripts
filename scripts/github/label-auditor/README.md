# label-auditor

## Purpose
Keep your issue labels consistent across projects. The tool fetches the labels of two or more repositories and shows where they disagree: labels that exist in some repositories but not others, the same label spelled with different capitalisation, and labels that have a different colour or description. It's the quick check to run before you standardise your triage setup.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python label_auditor.py owner/repo-one owner/repo-two [owner/repo-three ...]
python label_auditor.py --from-file saved-labels.json
```
The exit code is 1 when any difference is found and 0 when the labels all match. Public repositories need no login (60 requests an hour is plenty here); for private ones set `GITHUB_TOKEN` (`export GITHUB_TOKEN=ghp_...`, or `$env:GITHUB_TOKEN = "ghp_..."` in PowerShell). It is only sent to the GitHub API and never printed. The tool only reads labels; it never changes them. `--from-file` takes a JSON object mapping each repository to the list of labels GitHub returns.

## Example
```bash
python label_auditor.py --from-file gh-labels.json
```
```
Compared 3 repositories and 5 distinct label(s).

Missing from some repositories (3):
  'docs': missing in octo-demo/web-app
  'documentation': missing in octo-demo/api-server, octo-demo/data-tools
  'good first issue': missing in octo-demo/web-app, octo-demo/data-tools

Different colours (1):
  'bug': api-server=d73a4a; web-app=ee0701; data-tools=d73a4a

Different descriptions (1):
  'enhancement': api-server=New feature or request; web-app=New feature or request; data-tools=A new feature

5 difference(s) found.
```

## Notes
- Names are compared ignoring case and punctuation, so `Good First Issue` and `good-first-issue` count as the same label spelled differently.
- Colours are compared as hex codes without case, so `D73A4A` equals `d73a4a`.
- A label with no description counts as `(none)`.
- The website demo reads the sample file; live comparisons work on your own computer.
