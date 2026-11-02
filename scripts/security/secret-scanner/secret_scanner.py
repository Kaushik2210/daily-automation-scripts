"""Scan a folder for accidentally committed secrets such as API keys and private keys."""
import argparse
import os
import re
import sys
from pathlib import Path

PATTERNS = {
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "Slack token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "Stripe live key": re.compile(r"\b[rs]k_live_[0-9A-Za-z]{20,}\b"),
    "Private key block": re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"),
    "Hard-coded credential": re.compile(
        r"""(?i)\b(?:api[_-]?key|secret|token|passwd|password)\b\s*[:=]\s*['"][^'"\s]{8,}['"]"""),
}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".idea", ".vscode"}
PLACEHOLDERS = ("example", "your_", "your-", "changeme", "xxxx", "placeholder", "<", "${", "dummy")
MAX_BYTES = 2 * 1024 * 1024


def mask(text):
    """Show only the first and last 3 characters of a match."""
    return text if len(text) <= 8 else f"{text[:3]}{'*' * min(len(text) - 6, 10)}{text[-3:]}"


def scan_text(text):
    """Return a list of (line_number, kind, masked_match) found in `text`."""
    findings = []
    for number, line in enumerate(text.splitlines(), 1):
        for kind, pattern in PATTERNS.items():
            match = pattern.search(line)
            if match and not any(p in line.lower() for p in PLACEHOLDERS):
                findings.append((number, kind, mask(match.group(0))))
    return findings


def scan_folder(root):
    """Yield (path, line, kind, masked) for each suspicious line under `root`."""
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            path = Path(current) / name
            try:
                if path.stat().st_size > MAX_BYTES:
                    continue
                text = path.read_bytes().decode("utf-8")
            except (OSError, UnicodeDecodeError):
                continue  # unreadable or binary
            for number, kind, masked in scan_text(text):
                yield path, number, kind, masked


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find secrets left in files.")
    parser.add_argument("folder", type=Path, nargs="?", default=Path("."))
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")

    count = 0
    for path, number, kind, masked in scan_folder(args.folder):
        print(f"{path}:{number}  {kind}  {masked}")
        count += 1
    print(f"{count} possible secret(s) found." if count else "No secrets found.")
    return 1 if count else 0


if __name__ == "__main__":
    sys.exit(main())
