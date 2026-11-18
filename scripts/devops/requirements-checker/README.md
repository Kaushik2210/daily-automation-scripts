# requirements-checker

## Purpose
See which of your pinned Python packages have newer releases. The tool reads `package==version` lines from a requirements file, looks up each package's latest version on PyPI and tells you whether the update is a major, minor or patch change, so you can plan upgrades before an old version becomes a security problem. Lines without `==` (such as `numpy>=1.24`), comments and `-r` includes are ignored.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python requirements_checker.py requirements.txt [--latest latest.json] [--timeout 10]
```
By default each package is looked up on PyPI over the internet. `--latest` reads a saved JSON file such as `{"flask": "3.0.3"}` instead, which works offline and in tests. Set the `PYPI_URL` environment variable to use a private index that serves the same JSON API. The exit code is 1 when any package is outdated.

## Example
```bash
python requirements_checker.py requirements-demo.txt --latest latest-versions.json
```
```
{{OUTPUT}}
```

## Notes
- Versions are compared numerically, and pre-releases sort before the release.
- Packages the tool can't look up (private packages, no network) are listed with `?` and don't fail the run.
- A newer version isn't always safe to install; read the changelog for major updates.
- The website demo uses a saved version file; live lookups work on your own computer.
