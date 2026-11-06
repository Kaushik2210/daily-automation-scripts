"""Print a short report about this machine: OS, CPU, Python and memory."""
import argparse
import getpass
import json
import os
import platform
import shutil
import sys


def total_memory_bytes():
    """Physical memory in bytes, or None where the standard library can't tell."""
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, ValueError, OSError):
        return None


def gather():
    """Collect machine facts into an ordered dict."""
    memory = total_memory_bytes()
    disk = shutil.disk_usage(os.path.abspath(os.sep))
    try:
        user = getpass.getuser()
    except Exception:  # no login name available (some containers)
        user = "unknown"
    return {
        "hostname": platform.node(),
        "user": user,
        "os": f"{platform.system()} {platform.release()}",
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "cpu_count": os.cpu_count(),
        "memory_gb": round(memory / 1024**3, 1) if memory else None,
        "disk_total_gb": round(disk.total / 1024**3, 1),
        "disk_free_gb": round(disk.free / 1024**3, 1),
        "python": platform.python_version(),
        "python_path": sys.executable,
        "working_dir": os.getcwd(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Report basic facts about this machine.")
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    args = parser.parse_args(argv)

    info = gather()
    if args.json:
        print(json.dumps(info, indent=2))
        return 0
    width = max(len(key) for key in info)
    for key, value in info.items():
        print(f"{key.replace('_', ' '):<{width}}  {'n/a' if value is None else value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
