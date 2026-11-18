"""Report which pinned packages in a requirements.txt are behind their latest PyPI release."""
import argparse
import json
import os
import re
import sys
import urllib.error  # web-ok: PyPI is only queried without --latest
import urllib.request
from pathlib import Path

PIN = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?\s*==\s*([A-Za-z0-9.!+*_-]+)")


def normalise(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def version_key(text):
    """Sortable tuple for versions like 1.2.3 or 2.0rc1 (pre-releases sort before releases)."""
    parts = []
    for piece in re.split(r"[.+-]", text.lower().lstrip("v")):
        match = re.match(r"(\d+)(.*)", piece)
        if match:
            parts.append((int(match.group(1)), 1 if not match.group(2) else 0))
        else:
            parts.append((-1, 0))
    return parts


def bump(current, latest):
    a, b = (re.findall(r"\d+", v) for v in (current, latest))
    for index, name in enumerate(("major", "minor", "patch")):
        left = int(a[index]) if index < len(a) else 0
        right = int(b[index]) if index < len(b) else 0
        if right != left:
            return name
    return "other"


def parse_requirements(text):
    """Return [(line number, package, pinned version)] for lines using ==."""
    pins = []
    for number, line in enumerate(text.splitlines(), 1):
        match = PIN.match(line.split("#", 1)[0])
        if match:
            pins.append((number, match.group(1), match.group(2)))
    return pins


def latest_from_pypi(name, timeout):
    base = os.environ.get("PYPI_URL", "https://pypi.org/pypi").rstrip("/")
    request = urllib.request.Request(f"{base}/{name}/json",
                                     headers={"User-Agent": "daily-automation-scripts/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)["info"]["version"]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check pinned requirements for newer versions.")
    parser.add_argument("requirements", type=Path)
    parser.add_argument("--latest", type=Path,
                        help="JSON file {package: latest version} to use instead of asking PyPI")
    parser.add_argument("--timeout", type=float, default=10, help="seconds per PyPI request (10)")
    args = parser.parse_args(argv)
    if not args.requirements.is_file():
        parser.error(f"not a file: {args.requirements}")
    saved = {}
    if args.latest:
        try:
            saved = {normalise(k): v for k, v in json.loads(
                args.latest.read_text(encoding="utf-8")).items()}
        except (OSError, ValueError, AttributeError) as err:
            parser.error(f"can't read {args.latest}: {err}")

    pins = parse_requirements(args.requirements.read_text(encoding="utf-8", errors="replace"))
    if not pins:
        print("No pinned (==) requirements found.", file=sys.stderr)
        return 1
    outdated = unknown = 0
    for _, package, pinned in pins:
        try:
            latest = saved.get(normalise(package)) if args.latest else latest_from_pypi(
                package, args.timeout)
        except (urllib.error.URLError, OSError, KeyError, ValueError) as err:
            latest = None
            reason = getattr(err, "reason", err)
        else:
            reason = "not in the version file"
        if not latest:
            print(f"?  {package:<18} {pinned:<10} could not check ({reason})")
            unknown += 1
        elif version_key(latest) > version_key(pinned):
            print(f"!  {package:<18} {pinned:<10} -> {latest:<10} {bump(pinned, latest)} update")
            outdated += 1
        else:
            print(f"ok {package:<18} {pinned:<10} up to date")
    print(f"\n{len(pins)} pinned package(s): {outdated} outdated, {unknown} unchecked.")
    return 1 if outdated else 0


if __name__ == "__main__":
    sys.exit(main())
