"""Install ready-made git hooks (pre-commit checks, commit-message rules...) from templates."""
import argparse
import os
import stat
import subprocess  # web-ok: git is only asked where the hooks folder is; --hooks-dir avoids it
import sys
from pathlib import Path

MARKER = "# managed by git-hook-installer"
TYPES = "feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert"
PRESETS = {"python": ["ruff check .", "python -m pytest -q"], "node": ["npm test --silent"],
           "go": ["go vet ./...", "go test ./..."], "none": []}
DESCRIPTIONS = {
    "pre-commit": "runs your checks before every commit (blocks the commit if one fails)",
    "pre-push": "runs your checks before every push",
    "commit-msg": "requires Conventional Commit messages such as 'feat: add search'",
    "protect-branch": "refuses commits made directly on main or master",
}


def run_lines(commands, label):
    lines = []
    for command in commands:
        lines += [f'echo "{label}: {command}"',
                  f'{command} || {{ echo "{label}: failed: {command}" >&2; exit 1; }}']
    return lines or [f'echo "{label}: nothing configured (use --preset or --command)"']


def render(hook, commands):
    """The text of one hook script."""
    head = ["#!/bin/sh", f"{MARKER} (reinstall to change it, --uninstall to remove it)"]
    if hook in ("pre-commit", "pre-push"):
        body = ["set -e", *run_lines(commands, hook)]
    elif hook == "commit-msg":
        body = [
            'first_line=$(head -n 1 "$1")',
            'case "$first_line" in Merge*|Revert*|fixup!*|squash!*) exit 0 ;; esac',
            f"if echo \"$first_line\" | grep -Eq '^({TYPES})(\\([^)]+\\))?!?: .+'; then exit 0; fi",
            'echo "commit-msg: use the form type: description, e.g. feat: add search" >&2',
            f'echo "commit-msg: types are {TYPES.replace("|", ", ")}" >&2',
            "exit 1"]
    elif hook == "protect-branch":
        body = ['branch=$(git symbolic-ref --short HEAD 2>/dev/null || echo "")',
                'case "$branch" in main|master)',
                '  echo "protect-branch: don\'t commit straight to $branch; use a branch" >&2',
                "  exit 1 ;; esac"]
    else:
        raise ValueError(f"unknown hook '{hook}'")
    return "\n".join([*head, *body]) + "\n"


def hook_file(hook):
    """protect-branch is installed as a pre-commit hook."""
    return "pre-commit" if hook == "protect-branch" else hook


def hooks_dir(repo, override=None):
    if override:
        return override
    result = subprocess.run(["git", "-C", str(repo), "rev-parse", "--git-path", "hooks"],
                            capture_output=True, text=True, timeout=30, check=False)
    if result.returncode == 0 and result.stdout.strip():
        found = Path(result.stdout.strip())
        return found if found.is_absolute() else repo / found
    return repo / ".git" / "hooks"


def is_ours(path):
    return path.is_file() and MARKER in path.read_text(encoding="utf-8", errors="replace")


def backup_path(path):
    candidate, number = path.with_name(path.name + ".bak"), 1
    while candidate.exists():
        candidate = path.with_name(f"{path.name}.bak.{number}")
        number += 1
    return candidate


def installed(directory):
    """[(hook file name, 'ours' | 'someone else's' | 'sample')] for the hooks folder."""
    found = []
    for path in sorted(directory.iterdir()) if directory.is_dir() else []:
        if path.is_file() and not path.name.endswith((".bak",)) and ".bak." not in path.name:
            kind = "sample" if path.suffix == ".sample" else "ours" if is_ours(path) else "other"
            found.append((path.name, kind))
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description="Install git hooks from templates.")
    parser.add_argument("action", choices=["list", "install", "uninstall"])
    parser.add_argument("hooks", nargs="*", help=f"which hooks: {', '.join(DESCRIPTIONS)}")
    parser.add_argument("--repo", type=Path, default=Path("."), help="the repository (.)")
    parser.add_argument("--hooks-dir", type=Path, help="install into this folder instead")
    parser.add_argument("--preset", choices=list(PRESETS), default="none",
                        help="checks for pre-commit/pre-push: python, node, go (none)")
    parser.add_argument("--command", action="append", default=[],
                        help="a check to run in pre-commit/pre-push; repeat for several")
    parser.add_argument("--apply", action="store_true",
                        help="really change the hooks (default is a dry run)")
    args = parser.parse_args(argv)
    unknown = [h for h in args.hooks if h not in DESCRIPTIONS]
    if unknown:
        parser.error(f"unknown hook(s): {', '.join(unknown)} (choose from "
                     f"{', '.join(DESCRIPTIONS)})")
    try:
        directory = hooks_dir(args.repo, args.hooks_dir)
    except (OSError, subprocess.SubprocessError):
        directory = args.hooks_dir or args.repo / ".git" / "hooks"

    if args.action == "list":
        for name, description in DESCRIPTIONS.items():
            print(f"  {name:<15} {description}")
        print(f"\nHooks folder: {directory}")
        for name, kind in installed(directory):
            print(f"  {name:<26} {'installed by this tool' if kind == 'ours' else kind}")
        return 0
    if not args.hooks:
        parser.error(f"{args.action} needs at least one hook name")
    if args.action == "install" and not args.hooks_dir and not directory.parent.is_dir():
        print(f"{args.repo} doesn't look like a git repository (no {directory}).", file=sys.stderr)
        return 1

    commands = [*PRESETS[args.preset], *args.command]
    problems = 0
    for hook in args.hooks:
        target = directory / hook_file(hook)
        if args.action == "uninstall":
            if is_ours(target):
                print(f"{'removing' if args.apply else 'would remove'}  {target}")
                if args.apply:
                    target.unlink()
            else:
                print(f"skip {target}: " + ("not installed" if not target.exists()
                                             else "it wasn't installed by this tool"))
                problems += target.exists()
            continue
        text = render(hook, commands)
        note = "new"
        if target.exists():
            note = "replaces an older copy" if is_ours(target) else (
                f"existing hook is kept as {backup_path(target).name}")
        print(f"{'installing' if args.apply else 'would install'}  {hook} -> {target}  ({note})")
        if not args.apply:
            print("    " + "\n    ".join(text.splitlines()[2:6]))
            continue
        directory.mkdir(parents=True, exist_ok=True)
        if target.exists() and not is_ours(target):
            target.replace(backup_path(target))
        target.write_text(text, encoding="utf-8", newline="\n")
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    if not args.apply:
        print("\nDry run. Use --apply to do it.")
    if args.action == "install" and args.apply and os.name == "nt":
        print("(On Windows the hooks run through Git's own sh, so they work in Git Bash and Git "
              "GUI.)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
