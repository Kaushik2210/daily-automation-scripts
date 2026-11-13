# integrity-monitor

## Purpose
Notice when files change that shouldn't. Record a baseline of a folder (every file's size and SHA-256 hash, plus permissions on Linux and macOS), then check against it later: the tool reports files that were modified, added or removed, and files whose permissions changed. It is the idea behind professional file-integrity monitors, useful for a web root that might get defaced, a configuration folder, or a server directory you want to keep an eye on. A baseline can be signed with a secret so tampering with the baseline itself is caught too.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python integrity_monitor.py init  FOLDER --baseline baseline.json [--exclude PATTERN ...] [--key-env VAR]
python integrity_monitor.py check FOLDER --baseline baseline.json [--key-env VAR]
python integrity_monitor.py update FOLDER --baseline baseline.json --apply
```
`init` writes a new baseline (never over an existing one). `check` compares and exits with 1 if anything differs, so a scheduled job can alert you, and with 2 if a signed baseline fails verification. After an expected change, `update` shows what it would accept; add `--apply` to rewrite the baseline, which also keeps the old one as `baseline.json.<time>.prev`. To sign the baseline, put a long secret in an environment variable (for example `export FIM_KEY=...`) and pass `--key-env FIM_KEY` to `init`, `check` and `update`. Store the baseline somewhere an attacker on the monitored machine can't edit it. The monitored folder is only read.

## Example
```bash
python integrity_monitor.py check demo-project --baseline integrity-baseline.json
```
```
Compared 5 file(s) with the baseline of 2026-11-01T09:00:00: 4 unchanged.
  MODIFIED            src/utils.js
  REMOVED             docs/removed.md
2 change(s) found.
```

## Notes
- Logs and caches change constantly; leave them out with `--exclude` (for example `--exclude logs --exclude "*.tmp"`).
- Hashes prove content changed, not why; investigate every MODIFIED or ADDED line you didn't expect.
- Permission changes are only tracked on Linux and macOS.
- Symbolic links are skipped.
