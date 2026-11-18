"""Flag common Dockerfile mistakes: unpinned images, running as root, leaky layers and more."""
import argparse
import re
import sys
from pathlib import Path

SECRET_NAME = re.compile(r"PASSWORD|PASSWD|SECRET|TOKEN|API_?KEY|PRIVATE_?KEY|CREDENTIAL",
                         re.IGNORECASE)
SEVERITY = {"error": 0, "warn": 1, "info": 2}
INSTALL = re.compile(
    r"\b(npm (ci|install)|pip3? install|yarn install|bundle install|apt-get install)")


def parse(text):
    """Return [(line number, INSTRUCTION, arguments)], joining backslash continuations."""
    items, buffer, start = [], "", 0
    for number, raw in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
        line = raw.rstrip()
        if line.lstrip().startswith("#") or (not buffer and not line.strip()):
            continue
        start = start or number
        if line.endswith("\\"):
            buffer += line[:-1] + " "
            continue
        buffer += line
        parts = buffer.strip().split(None, 1)
        if parts:
            items.append((start, parts[0].upper(), parts[1] if len(parts) > 1 else ""))
        buffer, start = "", 0
    return items


def check_from(args):
    image = args.split()[0] if args.split() else ""
    if image.lower() == "scratch" or image.startswith("$") or "@sha256:" in image:
        return []
    name = image.rsplit("/", 1)[-1]
    if ":" not in name:
        return [("warn", "DL001", f"'{image}' has no tag, so it means :latest; pin a version")]
    if name.endswith(":latest"):
        return [("warn", "DL001", f"'{image}' uses :latest; pin a specific version")]
    return []


def check_add(args):
    source = args.split()[0] if args.split() else ""
    if re.match(r"https?://", source) or re.search(r"\.(tar|tgz|gz|bz2|xz)\b", source):
        return []
    return [("warn", "DL003", "Use COPY instead of ADD for plain files (ADD has hidden extras)")]


def check_run(args):
    lowered, found = args.lower(), []
    if re.search(r"apt-get\s+(?:-\S+\s+)*install", lowered):
        if not re.search(r"\s-y\b|--yes|--assume-yes|-qq?y|-yq", lowered):
            found.append(("error", "DL004", "apt-get install without -y waits for input and fails"))
        if "--no-install-recommends" not in lowered:
            found.append(("info", "DL004", "Add --no-install-recommends to keep the image smaller"))
        if "/var/lib/apt/lists" not in lowered:
            found.append(("warn", "DL004", "Remove /var/lib/apt/lists/* in the same RUN"))
        if "apt-get update" not in lowered:
            found.append(("warn", "DL004", "Run 'apt-get update' in the same RUN as install"))
    if re.search(r"pip3?\s+install", lowered) and "--no-cache-dir" not in lowered:
        found.append(("warn", "DL005", "pip install without --no-cache-dir keeps its cache"))
    if re.search(r"(^|[;&|]\s*)cd\s", lowered):
        found.append(("warn", "DL006", "Use WORKDIR instead of 'cd' inside RUN"))
    if re.search(r"\bsudo\b", lowered):
        found.append(("warn", "DL008", "sudo is not needed: build steps already run as root"))
    if re.search(r"(curl|wget)[^|;]*\|\s*(sudo\s+)?(ba|z)?sh\b", lowered):
        found.append(("error", "DL009", "Piping a download into a shell runs unverified code"))
    return found


def check_env(args):
    pairs = re.findall(r"([A-Za-z_][A-Za-z0-9_]*)=(\S+)", args)
    if not pairs and len(args.split(None, 1)) == 2:
        pairs = [tuple(args.split(None, 1))]
    return [("error", "DL011", f"{name} looks like a secret baked into the image")
            for name, value in pairs if SECRET_NAME.search(name) and value.strip("\"'")]


def check_workdir(args):
    if args.startswith(("/", "$", '"/', "'/")) or re.match(r"^[A-Za-z]:", args):
        return []
    return [("warn", "DL013", f"WORKDIR '{args}' is relative; use an absolute path")]


def check_expose(args):
    if re.search(r"(^|\s)22(/|\s|$)", args):
        return [("warn", "DL010", "Port 22 suggests SSH in a container; use docker exec instead")]
    return []


CHECKS = {"FROM": check_from, "ADD": check_add, "RUN": check_run, "ENV": check_env,
          "ARG": check_env, "WORKDIR": check_workdir, "EXPOSE": check_expose}


def lint(text):
    """Return a sorted list of (line, severity, rule id, message)."""
    items, found = parse(text), []
    stages = [i for i, (_, kind, _) in enumerate(items) if kind == "FROM"]
    if not stages:
        return [(1, "error", "DL000", "No FROM instruction: this is not a valid Dockerfile")]
    pending_copy = None
    for line, kind, args in items:
        found += [(line, *item) for item in CHECKS.get(kind, lambda _: [])(args)]
        if kind == "COPY" and re.match(r"^(--\S+\s+)*\.\s+\S+", args) and pending_copy is None:
            pending_copy = line
        if kind == "RUN" and pending_copy and INSTALL.search(args.lower()):
            found.append((pending_copy, "info", "DL014",
                          "COPY . . before installing dependencies breaks the build cache; "
                          "copy the dependency file first"))
            pending_copy = None
        if kind == "FROM":
            pending_copy = None
    for kind in ("CMD", "ENTRYPOINT"):
        lines = [n for n, k, _ in items if k == kind]
        if len(lines) > 1:
            found.append((lines[-1], "warn", "DL007",
                          f"{len(lines)} {kind} instructions; only the last one has an effect"))
    final = items[stages[-1]:]
    if not any(kind == "USER" for _, kind, _ in final):
        found.append((items[stages[-1]][0], "warn", "DL002",
                      "No USER instruction: the container runs as root"))
    if not any(kind == "HEALTHCHECK" for _, kind, _ in items):
        found.append((items[stages[-1]][0], "info", "DL012", "No HEALTHCHECK defined"))
    return sorted(found, key=lambda f: (f[0], SEVERITY[f[1]]))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Lint a Dockerfile.")
    parser.add_argument("dockerfile", type=Path)
    parser.add_argument("--strict", action="store_true", help="exit with 1 on warnings too")
    parser.add_argument("--ignore", default="", help="comma-separated rule ids to skip, e.g. DL012")
    args = parser.parse_args(argv)
    if not args.dockerfile.is_file():
        parser.error(f"not a file: {args.dockerfile}")

    skip = {r.strip().upper() for r in args.ignore.split(",") if r.strip()}
    results = [r for r in lint(args.dockerfile.read_text(encoding="utf-8", errors="replace"))
               if r[2] not in skip]
    for line, severity, rule, message in results:
        print(f"{args.dockerfile.name}:{line}  {severity.upper():<5} {rule}  {message}")
    counts = {s: sum(1 for r in results if r[1] == s) for s in SEVERITY}
    print(f"\n{counts['error']} error(s), {counts['warn']} warning(s), "
          f"{counts['info']} suggestion(s).")
    return 1 if counts["error"] or (args.strict and counts["warn"]) else 0


if __name__ == "__main__":
    sys.exit(main())
