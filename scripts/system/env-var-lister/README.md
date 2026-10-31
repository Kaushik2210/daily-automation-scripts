# env-var-lister

## Purpose
Look through your environment variables without leaking secrets onto the screen or into a screenshot. Variables whose names contain KEY, TOKEN, SECRET, PASSWORD and similar words are masked.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python env_var_lister.py [SEARCH] [--names-only] [--show-secrets]
```
`SEARCH` matches part of a name or a value, ignoring case.

## Example
```bash
python env_var_lister.py token
```
```
GITHUB_TOKEN=gh************yz
NPM_TOKEN=np**********9a
2 variable(s).
```

## Notes
- Masked values keep the first and last two characters so you can tell tokens apart.
- `--show-secrets` prints everything, so only use it somewhere private.
- Read-only; the count goes to stderr so piped output stays clean.
