"""Audit a .env file for empty, duplicate, weak or missing values. Values are never printed."""
import argparse
import re
import sys
from pathlib import Path

SECRET_NAME = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|PASSWD|PWD|CREDENTIAL|AUTH", re.IGNORECASE)
WEAK = {"password", "admin", "secret", "changeme", "123456", "test", "root", "default", "letmein"}
PLACEHOLDER = re.compile(r"^(your[_-].*|<.*>|\$\{.*\}|x{3,}|\*{3,}|todo|replace.?me|change.?me)$",
                         re.IGNORECASE)


def parse_env(text):
    """Return a list of (line_number, name, value) for KEY=VALUE lines."""
    entries = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = line.removeprefix("export ").strip()
        name, sep, value = line.partition("=")
        if sep:
            entries.append((number, name.strip(), value.strip().strip("'\"")))
    return entries


def audit(entries, example_names=None):
    """Return a list of (line_number, name, problem) strings; values are never included."""
    problems, seen = [], {}
    for number, name, value in entries:
        if name in seen:
            problems.append((number, name, f"duplicate of line {seen[name]}"))
        seen.setdefault(name, number)
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            problems.append((number, name, "name has unusual characters"))
        if not value:
            problems.append((number, name, "is empty"))
        elif PLACEHOLDER.match(value):
            problems.append((number, name, "still holds a placeholder"))
        elif SECRET_NAME.search(name) and (value.lower() in WEAK or len(value) < 8):
            problems.append((number, name, "looks like a weak secret"))
    if example_names is not None:
        for name in sorted(example_names - set(seen)):
            problems.append((0, name, "is in the example file but missing here"))
    return problems


def gitignored(env_path, gitignore_text):
    names = {line.strip().lstrip("/") for line in gitignore_text.splitlines()}
    return any(pattern in names for pattern in (env_path.name, ".env", ".env*", "*.env"))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit a .env file.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--example", type=Path, help="a .env.example to compare names against")
    parser.add_argument("--gitignore", type=Path, help=".gitignore to check the file is excluded")
    args = parser.parse_args(argv)
    if not args.file.is_file():
        parser.error(f"not a file: {args.file}")

    entries = parse_env(args.file.read_text(encoding="utf-8-sig"))
    example = None
    if args.example:
        example = {name for _, name, _ in parse_env(args.example.read_text(encoding="utf-8-sig"))}
    problems = audit(entries, example)
    ignore_text = args.gitignore.read_text(encoding="utf-8") if args.gitignore else None
    if ignore_text is not None and not gitignored(args.file, ignore_text):
        problems.append((0, args.file.name, "is NOT listed in .gitignore"))
    for number, name, problem in problems:
        where = f"line {number}" if number else "file"
        print(f"{where:<8} {name}  {problem}")
    print(f"{len(entries)} variable(s) checked, {len(problems)} problem(s).")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
