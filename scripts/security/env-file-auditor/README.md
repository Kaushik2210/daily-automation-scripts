# env-file-auditor

## Purpose
Check a `.env` file before it causes trouble: empty values, leftover placeholders, weak secrets, duplicate names, variables that exist in `.env.example` but are missing, and whether the file is excluded by `.gitignore`. It only talks about names and line numbers, so values never appear in the output.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python env_file_auditor.py FILE [--example .env.example] [--gitignore .gitignore]
```
The exit code is 1 when any problem is found.

## Example
```bash
python env_file_auditor.py .env --example .env.example --gitignore .gitignore
```
```
line 2   DB_PASSWORD  looks like a weak secret
line 5   STRIPE_KEY  is empty
file     SMTP_HOST  is in the example file but missing here
12 variable(s) checked, 3 problem(s).
```

## Notes
- A secret counts as weak if its name contains KEY, TOKEN, SECRET or PASSWORD and the value is shorter than 8 characters or a common word.
- `export NAME=value` lines and quoted values are understood.
- Read-only. Never commit your real `.env` file; commit a `.env.example` with placeholder values instead.
