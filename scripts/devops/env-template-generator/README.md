# env-template-generator

## Purpose
Create a safe `.env.example` from your real `.env` file, so teammates know which settings the project needs without ever seeing your passwords. Every variable and comment is kept in the same order, but the values are removed (or replaced with a placeholder). If an example file already exists, the tool doesn't touch it; it tells you which variables are missing from it and which are no longer used.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python env_template_generator.py .env [--keep-safe] [--placeholder TEXT] [-o OUTPUT] [--apply]
```
Dry run by default: it prints the template and says what it would write. With `--apply` it creates `.env.example` next to the input (or `-o`). `--keep-safe` keeps harmless values such as `true`, `8080` or `localhost` but still removes anything that looks secret (keys containing PASS, SECRET, TOKEN, KEY..., or URLs with credentials). Quotes, `export` prefixes and trailing comments are handled. The exit code is 1 if an existing example file is missing variables.

## Example
```bash
python env_template_generator.py app.env --keep-safe
```
```
{{OUTPUT}}
```

## Notes
- Run it in CI to make sure `.env.example` never falls behind `.env`.
- The real `.env` is only read, never changed. Remember to keep it in `.gitignore`.
- Use `secret-scanner` to look for secrets that slipped into other files.
