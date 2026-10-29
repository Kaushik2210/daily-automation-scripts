# Working rules

These rules apply to every script in this repo, whoever is writing it.

## Structure
- One script = one folder = one commit = one push.
- Layout: `scripts/<category>/<script-name>/` containing `<script_name>.py`, `README.md`, `test_<script_name>.py` and, only if non-stdlib packages are used, `requirements.txt`.
- Folder names are kebab-case, Python files are snake_case. Use the name exactly as written in `PLAN.md`.
- Keep each script focused: roughly 30 to 150 lines. Quality over padding.

## Script requirements
- Python 3.11+, standard library first. Third-party packages only when really needed, listed in the script's `requirements.txt`.
- Every script is a CLI built with `argparse`, has `--help`, and runs on Windows, macOS and Linux (use `pathlib`, no shell-only tricks).
- Anything that modifies, renames or deletes files MUST default to `--dry-run` and require an explicit `--apply` flag.
- Never hardcode secrets. Read tokens from environment variables and document them in the script README. Never commit `.env` files.

## Script README sections
Purpose, Install, Usage, Example, Notes.

## Tests
- pytest, at least 2 tests per script.
- No network access in tests; mock external calls.
- Tests must pass before committing.

## Commit workflow
1. Run `ruff check` and `pytest` on the script's folder.
2. Commit with the message format `day-<DD>/<NN>: <script-name> - <one-line description>`. Write the description like a person would, short and plain.
3. Run `python tools/update_index.py`, stage the result and amend it into the same commit.
4. `git push`.

If a push fails, stop and report the error. Never force-push.
