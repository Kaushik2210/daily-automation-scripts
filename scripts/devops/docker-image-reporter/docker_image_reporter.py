"""Report the sizes of local Docker images: the biggest ones, dangling images and totals."""
import argparse
import json
import re
import shutil
import subprocess  # web-ok: docker is only run without --from-file; saved output works anywhere
import sys
from pathlib import Path

UNITS = {"b": 1, "kb": 1000, "mb": 1000 ** 2, "gb": 1000 ** 3, "tb": 1000 ** 4}
BIG = 500 * 1000 ** 2


def to_bytes(text):
    """'1.02GB' / '245MB' / '12.3kB' / '0B' -> bytes (Docker uses decimal units)."""
    match = re.fullmatch(r"\s*([\d.]+)\s*([A-Za-z]+)\s*", text or "")
    if not match or match.group(2).lower() not in UNITS:
        raise ValueError(f"can't read the size {text!r}")
    return round(float(match.group(1)) * UNITS[match.group(2).lower()])


def human(size):
    for unit in ("B", "kB", "MB", "GB"):
        if size < 1000 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1000


def parse_images(text):
    """Parse `docker images --format '{{json .}}'` output (one JSON object per line)."""
    images = []
    for line in text.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        repo, tag = row.get("Repository", "<none>"), row.get("Tag", "<none>")
        images.append({"name": f"{repo}:{tag}" if repo != "<none>" else "<none>",
                       "repo": repo, "tag": tag, "id": row.get("ID", "")[:12],
                       "size": to_bytes(row.get("Size", "0B")), "age": row.get("CreatedSince", "")})
    return images


def run_docker():
    exe = shutil.which("docker")
    if not exe:
        raise OSError("docker was not found - install Docker or use --from-file")
    result = subprocess.run([exe, "images", "--format", "{{json .}}"], capture_output=True,
                            text=True, timeout=60, check=False)
    if result.returncode:
        raise OSError((result.stderr.strip().splitlines() or ["docker failed"])[-1])
    return result.stdout


def main(argv=None):
    parser = argparse.ArgumentParser(description="Report local Docker image sizes.")
    parser.add_argument("--from-file", type=Path, dest="source",
                        help="read saved output of: docker images --format '{{json .}}'")
    parser.add_argument("--top", type=int, default=10, help="how many images to list (10)")
    args = parser.parse_args(argv)
    try:
        text = args.source.read_text(encoding="utf-8") if args.source else run_docker()
        images = parse_images(text)
    except (OSError, ValueError, subprocess.TimeoutExpired) as err:
        print(f"Can't read the image list: {err}", file=sys.stderr)
        return 1
    if not images:
        print("No images found.")
        return 0

    images.sort(key=lambda i: -i["size"])
    print(f"{'IMAGE':<26} {'SIZE':>9}  {'CREATED':<14} ID")
    for image in images[:args.top]:
        flag = "  <- large" if image["size"] >= BIG and image["name"] != "<none>" else ""
        print(f"{image['name']:<26} {human(image['size']):>9}  {image['age']:<14} "
              f"{image['id']}{flag}")
    if len(images) > args.top:
        print(f"... and {len(images) - args.top} more")
    dangling = [i for i in images if i["name"] == "<none>"]
    total = sum(i["size"] for i in images)
    print(f"\n{len(images)} image(s), {human(total)} in total (shared layers are counted "
          f"once per image, so the real disk use is lower).")
    if dangling:
        print(f"{len(dangling)} dangling image(s) using {human(sum(i['size'] for i in dangling))}: "
              "remove them with 'docker image prune'.")
    repos = {}
    for image in images:
        if image["repo"] != "<none>":
            repos.setdefault(image["repo"], []).append(image)
    for repo, group in sorted(repos.items()):
        if len(group) > 1 and sum(i["size"] for i in group) >= BIG:
            print(f"{repo} has {len(group)} tags ({', '.join(i['tag'] for i in group)}) "
                  f"totalling {human(sum(i['size'] for i in group))}: old tags may be removable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
