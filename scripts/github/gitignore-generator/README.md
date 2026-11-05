# gitignore-generator

## Purpose
Start a repository with a sensible `.gitignore` in seconds. Pick the languages, editors and operating systems you use and get one combined file with no repeated lines.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python gitignore_generator.py STACK [STACK ...] [-o .gitignore --apply] [--append]
```
Available stacks: python, node, java, go, rust, dotnet, dotenv, macos, windows, linux, vscode, jetbrains, logs. The result is printed; to save it pass `-o` with `--apply`. An existing file is never overwritten unless you add `--append`, which adds only the lines it doesn't already have.

## Example
```bash
python gitignore_generator.py python dotenv macos
```
```
# python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
build/
dist/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/

# dotenv
.env
.env.*
!.env.example

# macos
.DS_Store
.AppleDouble
.LSOverride
._*
```

## Notes
- `dotenv` ignores `.env` files but keeps `.env.example` tracked.
- Lines already ignored by an earlier stack are not repeated.
- Check the result before committing; every project has its own odd files.
