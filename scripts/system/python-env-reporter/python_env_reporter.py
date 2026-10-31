"""List the Python packages installed in the current environment."""
import argparse
import json
import platform
import sys
from importlib import metadata


def installed_packages():
    """Return sorted {name: version}, one entry per distribution."""
    packages = {}
    for dist in metadata.distributions():
        name = dist.metadata["Name"]
        if name:
            packages[name] = dist.version
    return dict(sorted(packages.items(), key=lambda item: item[0].lower()))


def filter_packages(packages, search=""):
    needle = search.lower()
    return {n: v for n, v in packages.items() if needle in n.lower()}


def as_requirements(packages):
    return "\n".join(f"{name}=={version}" for name, version in packages.items())


def main(argv=None):
    parser = argparse.ArgumentParser(description="Report installed Python packages.")
    parser.add_argument("search", nargs="?", default="", help="only show names containing this")
    parser.add_argument("--format", choices=["table", "json", "requirements"], default="table")
    args = parser.parse_args(argv)

    packages = filter_packages(installed_packages(), args.search)
    if args.format == "json":
        print(json.dumps({"python": platform.python_version(), "packages": packages}, indent=2))
    elif args.format == "requirements":
        print(as_requirements(packages))
    else:
        print(f"Python {platform.python_version()} at {sys.executable}")
        width = max((len(n) for n in packages), default=4)
        for name, version in packages.items():
            print(f"{name:<{width}}  {version}")
        print(f"{len(packages)} package(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
