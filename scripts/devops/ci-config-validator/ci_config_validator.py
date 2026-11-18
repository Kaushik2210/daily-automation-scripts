"""Validate GitHub Actions workflow files: structure, pinned actions and risky patterns."""
import argparse
import re
import sys
from pathlib import Path

import yaml

TOP_KEYS = {"name", "run-name", "on", "permissions", "env", "defaults", "concurrency", "jobs"}
TRIGGERS = {"push", "pull_request", "pull_request_target", "workflow_dispatch", "workflow_call",
            "schedule", "release", "create", "delete", "fork", "issues", "issue_comment",
            "workflow_run", "repository_dispatch", "page_build", "watch", "deployment", "status",
            "check_run", "check_suite", "discussion", "label", "milestone", "public", "merge_group"}
LATEST = {"actions/checkout": 4, "actions/setup-python": 5, "actions/setup-node": 4,
          "actions/setup-java": 4, "actions/setup-go": 5, "actions/cache": 4,
          "actions/upload-artifact": 4, "actions/download-artifact": 4}
UNTRUSTED = re.compile(r"\$\{\{\s*github\.(event\.(pull_request\.(title|body|head\.ref|head\.label)"
                       r"|issue\.(title|body)|comment\.body|review\.body|head_commit\.message)"
                       r"|head_ref)\s*\}\}")
SEVERITY = {"error": 0, "warn": 1, "info": 2}


def check_uses(uses, where):
    found = []
    if uses.startswith(("./", "docker://")):
        return found
    if "@" not in uses:
        return [("error", where, f"'{uses}' has no version; add @v1, @sha or a tag")]
    name, ref = uses.rsplit("@", 1)
    if ref in ("main", "master", "latest", "HEAD"):
        found.append(("warn", where, f"'{uses}' follows a moving branch; pin a tag or commit sha"))
    match = re.fullmatch(r"v(\d+)(?:\.\d+)*", ref)
    if match and name.lower() in LATEST and int(match.group(1)) < LATEST[name.lower()]:
        found.append(("warn", where,
                      f"{name}@{ref} is old; the current major is v{LATEST[name.lower()]}"))
    return found


def validate(text):
    """Return a sorted list of (severity, where, message) for one workflow file."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as err:
        mark = getattr(err, "problem_mark", None)
        line = f" at line {mark.line + 1}" if mark else ""
        return [("error", "file", f"not valid YAML{line}: {getattr(err, 'problem', err)}")]
    if not isinstance(data, dict):
        return [("error", "file", "a workflow must be a YAML mapping with 'on' and 'jobs'")]
    found = []
    triggers = data.get("on", data.get(True))  # YAML 1.1 reads the key `on` as True
    if triggers is None:
        found.append(("error", "file", "missing 'on': say when the workflow should run"))
    else:
        names = (list(triggers) if isinstance(triggers, dict)
                 else [triggers] if isinstance(triggers, str) else list(triggers))
        found += [("warn", "on", f"unknown trigger '{name}'") for name in names
                  if str(name) not in TRIGGERS]
    for key in data:
        if key not in TOP_KEYS and key is not True:
            found.append(("warn", "file", f"unknown top-level key '{key}'"))
    jobs = data.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        found.append(("error", "file", "missing 'jobs' (at least one job is required)"))
        return sorted(found, key=lambda f: SEVERITY[f[0]])
    if "permissions" not in data and not any(
            isinstance(j, dict) and "permissions" in j for j in jobs.values()):
        found.append(("info", "file", "no 'permissions': the token gets the repository default"))
    for job_id, job in jobs.items():
        where = f"jobs.{job_id}"
        if not isinstance(job, dict):
            found.append(("error", where, "a job must be a mapping"))
            continue
        reusable = "uses" in job
        if "runs-on" not in job and not reusable:
            found.append(("error", where, "missing 'runs-on'"))
        needs = job.get("needs", [])
        for need in [needs] if isinstance(needs, str) else needs:
            if need not in jobs:
                found.append(("error", where, f"needs '{need}', but there is no such job"))
        if reusable:
            found += check_uses(str(job["uses"]), where)
            continue
        if "timeout-minutes" not in job:
            found.append(("info", where, "no 'timeout-minutes' (a stuck job runs up to 6 hours)"))
        steps = job.get("steps")
        if not isinstance(steps, list) or not steps:
            found.append(("error", where, "missing 'steps'"))
            continue
        ids = {}
        for number, step in enumerate(steps, 1):
            label = f"{where}.steps[{number}]"
            if not isinstance(step, dict):
                found.append(("error", label, "a step must be a mapping"))
                continue
            name = step.get("name")
            if name:
                label += f" ({name})"
            if "uses" in step and "run" in step:
                found.append(("error", label, "a step can have 'uses' or 'run', not both"))
            elif "uses" not in step and "run" not in step:
                found.append(("error", label, "a step needs 'uses' or 'run'"))
            if "uses" in step:
                found += check_uses(str(step["uses"]), label)
            if UNTRUSTED.search(str(step.get("run", ""))):
                found.append(("warn", label, "untrusted text (PR title, branch, comment...) in "
                                              "'run' can inject commands; pass it through env"))
            if "id" in step:
                if step["id"] in ids:
                    found.append(("error", label, f"duplicate step id '{step['id']}' "
                                                  f"(also steps[{ids[step['id']]}])"))
                ids.setdefault(step["id"], number)
    return sorted(found, key=lambda f: SEVERITY[f[0]])


def collect(paths):
    files = []
    for path in paths:
        if path.is_dir():
            files += sorted(p for p in path.rglob("*") if p.suffix.lower() in (".yml", ".yaml"))
        elif path.is_file():
            files.append(path)
        else:
            print(f"not found: {path}", file=sys.stderr)
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate GitHub Actions workflow files.")
    parser.add_argument("paths", nargs="+", type=Path, help="workflow files or folders")
    parser.add_argument("--strict", action="store_true", help="exit with 1 on warnings too")
    args = parser.parse_args(argv)
    files = collect(args.paths)
    if not files:
        print("No workflow files found.", file=sys.stderr)
        return 1
    counts = {"error": 0, "warn": 0, "info": 0}
    for path in files:
        results = validate(path.read_text(encoding="utf-8", errors="replace"))
        print(f"{path}: " + ("OK" if not results else f"{len(results)} finding(s)"))
        for severity, where, message in results:
            counts[severity] += 1
            print(f"  {severity.upper():<5} {where}: {message}")
    print(f"\n{len(files)} file(s): {counts['error']} error(s), {counts['warn']} warning(s), "
          f"{counts['info']} suggestion(s).")
    return 1 if counts["error"] or (args.strict and counts["warn"]) else 0


if __name__ == "__main__":
    sys.exit(main())
