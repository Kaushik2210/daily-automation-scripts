# secret-scanner

## Purpose
Catch credentials before they leak. Scans every text file in a folder for AWS keys, GitHub and Slack tokens, Google and Stripe keys, private key blocks and hard-coded `password = "..."` style assignments.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python secret_scanner.py [FOLDER]
```
The exit code is 1 when something is found, so it works as a pre-commit or CI check.

## Example
```bash
python secret_scanner.py ./my-project
```
```
my-project/config.py:12  AWS access key  AKI**********XYZ
my-project/deploy.sh:4  Hard-coded credential  pas**********ue"
2 possible secret(s) found.
```

## Notes
- Matches are masked in the output, so the report itself doesn't leak anything.
- Lines containing placeholders such as `your_key`, `example` or `${...}` are ignored.
- `.git`, `node_modules`, virtual environments, binary files and files over 2 MB are skipped.
- It is a quick pattern check, not a full audit. If a real secret turns up, rotate it: deleting it from the file doesn't remove it from history.
