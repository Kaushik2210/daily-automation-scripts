# history-secret-scanner

## Purpose
Scan every commit on every branch for leaked secrets (cloud keys, tokens, private keys,
hard-coded passwords). Deleting a secret from the latest version doesn't remove it from history,
so this shows which commit added it and whether a later commit took it out.

## Install
No dependencies beyond Python 3.11+ and `git`.

## Usage
```
python history_secret_scanner.py
python history_secret_scanner.py --repo ~/code/app --since "6 months ago"
python history_secret_scanner.py --max-count 200 --format json
python history_secret_scanner.py --from-file history.patch --include-placeholders
```

`history.patch` can be made with `git log -p --all -U0 > history.patch`.

It only reads the repository. Secrets are always shown masked (first and last three characters).
Exit code is 1 when anything is found, which suits a CI check; add `--exit-zero` to just report.

## Example
`--from-file git-history.patch --include-placeholders`

```
4 possible secret(s) in the history:

  AWS access key: AKI**********PLE
    deploy/config.env  commit 9f3a1c2d by Dev One <dev1@example.com>
    Mon Nov 3 10:12:00 2026 +0000  (removed in 5e4d3c2b, still in history)
  Hard-coded credential: cor**********ple
    deploy/config.env  commit 9f3a1c2d by Dev One <dev1@example.com>
    Mon Nov 3 10:12:00 2026 +0000  (removed in 5e4d3c2b, still in history)
  Hard-coded credential: not**********890
    notes/todo.md  commit 7a6b5c4d by Dev One <dev1@example.com>
    Wed Nov 5 09:05:00 2026 +0000  (no later removal found)
  Private key block: ---**********---
    keys/id_deploy  commit 7a6b5c4d by Dev One <dev1@example.com>
    Wed Nov 5 09:05:00 2026 +0000  (no later removal found)

A secret that was ever committed must be treated as leaked: rotate it first, then clean the history if you need to.
```

## Notes
- Only added lines are scanned. A removed line is used to mark an earlier finding as "removed".
- Values that look like examples or placeholders are skipped unless you pass
  `--include-placeholders`.
- This is a pattern check, so expect some false positives and some misses. Treat every real hit
  as leaked: rotate the secret before cleaning history.
