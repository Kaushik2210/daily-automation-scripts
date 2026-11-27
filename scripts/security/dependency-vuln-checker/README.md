# dependency-vuln-checker

## Purpose
Check the exact versions your project depends on against the OSV vulnerability database, which
collects advisories for PyPI, npm and many other ecosystems, and see which ones have known
security problems and which version fixes them.

## Install
No dependencies beyond Python 3.11+.

## Usage
```
python dependency_vuln_checker.py requirements.txt
python dependency_vuln_checker.py package-lock.json
python dependency_vuln_checker.py package.json                  # only exact versions can be checked
python dependency_vuln_checker.py requirements.txt --fail-on high
python dependency_vuln_checker.py requirements.txt --ignore GHSA-xxxx-xxxx-xxxx --format json
python dependency_vuln_checker.py requirements.txt --db saved-advisories.json    # no network
```

- It reads `requirements.txt` files, `package.json` and `package-lock.json`. A vulnerability depends
  on the exact version, so only `name==1.2.3` lines (and exact versions in `package.json`) can be
  checked; ranges such as `>=2` or `^4.18.0` are listed as "not checked". A lock file is the best
  input for npm because it records the versions that were really installed.
- **What is sent:** only package names, ecosystem names and version numbers, to `api.osv.dev` (or
  the server you give with `--osv-url` or `$OSV_API_URL`). No file contents, paths or other details.
- The exit code is 1 if any finding is at least `--fail-on` (default `low`, so any). A finding whose
  severity isn't known also counts. `--ignore` skips an advisory by id or alias (for example a CVE)
  once you have decided it doesn't apply to you.
- `--db FILE` uses a saved JSON database instead of the network. Its format is
  `{"PyPI:name": [{"id", "summary", "severity", "introduced", "fixed"}]}`.

## Example
`requirements-pinned.txt --db osv-demo-db.json`

```
Checked 6 pinned package(s) against saved database osv-demo-db.json.

[CRITICAL] pyyaml==5.3: DEMO-2026-0003
    Demo advisory: unsafe load of tags
    fixed in 5.4

[HIGH] requests==2.19.0: DEMO-2026-0001
    Demo advisory: header leak on redirect
    fixed in 2.20.0

[MEDIUM] flask==2.0.1: DEMO-2026-0002
    Demo advisory: debug page exposed
    fixed in 2.0.3

[LOW] pyyaml==5.3: DEMO-2026-0004
    Demo advisory: slow regex
    fixed in 5.3.1
```

## Notes
- The demo database contains **invented advisories** (ids start with `DEMO-`), so the example doesn't
  claim anything about real packages. Real runs use the live OSV data.
- Version comparison uses the numeric part (so `1.10.0rc1` counts as `1.10.0`); the live OSV answers
  are computed by OSV itself and are not affected by this.
- "No known vulnerabilities" means none are published yet, not that the code is safe.
