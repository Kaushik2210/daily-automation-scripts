"""Find risky file permissions on Linux and macOS, and optionally tighten them."""
import argparse
import os
import stat
import sys
from pathlib import Path

KEY_NAMES = ("id_rsa", "id_dsa", "id_ecdsa", "id_ed25519")
KEY_SUFFIXES = (".pem", ".key", ".p12", ".pfx")
SKIP_DIRS = {".git", "node_modules", "__pycache__"}


def classify(mode, is_dir, name):
    """Return a list of (problem, safer_mode) for one file's permission bits."""
    problems = []
    if not is_dir and mode & stat.S_IWOTH:
        problems.append(("world-writable file", mode & ~stat.S_IWOTH))
    if is_dir and mode & stat.S_IWOTH and not mode & stat.S_ISVTX:
        problems.append(("world-writable folder without sticky bit", mode & ~stat.S_IWOTH))
    if not is_dir and mode & (stat.S_ISUID | stat.S_ISGID):
        problems.append(("setuid/setgid file", mode & ~(stat.S_ISUID | stat.S_ISGID)))
    is_key = name in KEY_NAMES or name.lower().endswith(KEY_SUFFIXES)
    if is_key and mode & (stat.S_IRWXG | stat.S_IRWXO):
        problems.append(("private key readable by others", stat.S_IMODE(mode) & 0o700))
    return problems


def audit(root):
    """Yield (path, problem, current_mode, safer_mode) for everything under `root`."""
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in [*dirs, *files]:
            path = Path(current) / name
            try:
                info = path.lstat()
            except OSError:
                continue
            if stat.S_ISLNK(info.st_mode):
                continue
            for problem, safer in classify(info.st_mode, path.is_dir(), name):
                yield path, problem, stat.S_IMODE(info.st_mode), stat.S_IMODE(safer)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit file permissions under a folder.")
    parser.add_argument("folder", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--apply", action="store_true",
                        help="really tighten the permissions (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")
    if os.name == "nt":
        print("Unix permission bits don't apply on Windows; nothing to audit.")
        return 0

    count = 0
    for path, problem, current, safer in audit(args.folder):
        print(f"{current:04o} -> {safer:04o}  {problem}: {path}")
        if args.apply:
            path.chmod(safer)
        count += 1
    verb = "Fixed" if args.apply else "Would fix"
    hint = "" if args.apply else " Use --apply to do it."
    print(f"{verb} {count} issue(s)." if count else "No risky permissions found.")
    if count and not args.apply:
        print(hint.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
