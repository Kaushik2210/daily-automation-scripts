"""Check pinned dependencies against the OSV vulnerability database (or a saved copy of it)."""
import argparse
import json
import os
import re
import sys
import urllib.error  # web-ok: the network is only used for live checks; --db works offline
import urllib.request
from pathlib import Path
from urllib.parse import quote, urlparse

OSV_URL = os.environ.get("OSV_API_URL", "https://api.osv.dev").rstrip("/")
USER_AGENT = "daily-automation-scripts/1.0 (dependency vuln checker)"
SEVERITY = {"critical": 4, "high": 3, "moderate": 2, "medium": 2, "low": 1, "unknown": 0}
BATCH = 100


def normalise(name, ecosystem):
    """PyPI names ignore case and treat -, _ and . alike; npm names are case-sensitive."""
    return re.sub(r"[-_.]+", "-", name).lower() if ecosystem == "PyPI" else name


def parse_requirements(text):
    """Return (pinned deps, entries that could not be checked)."""
    deps, skipped = [], []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split(" #", 1)[0].split(";", 1)[0].strip()
        if not line or line.startswith(("#", "-", "http", "git+")):
            continue
        match = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?\s*(==|===)\s*"
                         r"([A-Za-z0-9.!+_-]+)$", line)
        if match:
            deps.append({"name": match.group(1), "version": match.group(4), "line": number,
                         "ecosystem": "PyPI"})
        else:
            skipped.append(f"{line} (not pinned with ==)")
    return deps, skipped


def parse_package_json(text):
    data = json.loads(text)
    deps, skipped = [], []
    for section in ("dependencies", "devDependencies", "optionalDependencies"):
        for name, version in (data.get(section) or {}).items():
            if re.fullmatch(r"\d+\.\d+\.\d+([-+][\w.-]+)?", str(version)):
                deps.append({"name": name, "version": version, "line": 0, "ecosystem": "npm"})
            else:
                skipped.append(f"{name}@{version} (a range, not an exact version)")
    return deps, skipped


def parse_package_lock(text):
    data = json.loads(text)
    deps, seen = [], set()
    for path, info in (data.get("packages") or {}).items():
        name = info.get("name") or path.rsplit("node_modules/", 1)[-1]
        if path and info.get("version") and (name, info["version"]) not in seen:
            seen.add((name, info["version"]))
            deps.append({"name": name, "version": info["version"], "line": 0, "ecosystem": "npm"})
    return deps, []


def read_dependencies(path):
    text = path.read_text(encoding="utf-8-sig")
    name = path.name.lower()
    if name == "package-lock.json":
        return parse_package_lock(text)
    if name == "package.json":
        return parse_package_json(text)
    return parse_requirements(text)


def version_key(version):
    """The leading dotted number of a version: '1.10.2rc1' -> (1, 10, 2). Pre-release tags are
    ignored, so a release candidate compares equal to its final release."""
    match = re.match(r"v?(\d+(?:\.\d+)*)", version.split("+")[0])
    return tuple(int(n) for n in match.group(1).split("."))[:6] if match else (0,)


def from_db(db, dep):
    """Advisories in a saved database that cover this dependency's version."""
    entries = db.get(f"{dep['ecosystem']}:{normalise(dep['name'], dep['ecosystem'])}", [])
    version = version_key(dep["version"])
    found = []
    for adv in entries:
        introduced = version_key(adv.get("introduced") or "0")
        fixed = adv.get("fixed")
        if introduced <= version and (not fixed or version < version_key(fixed)):
            found.append({"id": adv["id"], "aliases": adv.get("aliases", []),
                          "summary": adv.get("summary", ""),
                          "severity": str(adv.get("severity", "unknown")).lower(),
                          "fixed": [fixed] if fixed else []})
    return found


def api(path, body=None, base=None):
    url = (base or OSV_URL) + path
    if urlparse(url).scheme not in ("http", "https"):
        raise ValueError("the OSV address must start with http:// or https://")
    data = json.dumps(body).encode() if body is not None else None
    headers = {"User-Agent": USER_AGENT, "Content-Type": "application/json"}
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def summarise_vuln(vuln, dep):
    """Reduce a full OSV record to id, summary, severity and the versions that fix it."""
    severity = str((vuln.get("database_specific") or {}).get("severity", "unknown")).lower()
    fixed = []
    for affected in vuln.get("affected", []):
        package = affected.get("package", {})
        if normalise(package.get("name", ""), dep["ecosystem"]) != normalise(dep["name"],
                                                                             dep["ecosystem"]):
            continue
        for rng in affected.get("ranges", []):
            fixed += [e["fixed"] for e in rng.get("events", []) if "fixed" in e]
    text = vuln.get("summary") or " ".join((vuln.get("details") or "").split())[:100]
    return {"id": vuln["id"], "aliases": vuln.get("aliases", []), "summary": text,
            "severity": severity, "fixed": sorted(set(fixed), key=version_key)}


def from_osv(deps, base=None, max_details=200):
    """Ask OSV about every dependency. Returns {index: [advisories]}."""
    hits = {}
    for start in range(0, len(deps), BATCH):
        chunk = deps[start:start + BATCH]
        queries = [{"package": {"name": d["name"], "ecosystem": d["ecosystem"]},
                    "version": d["version"]} for d in chunk]
        results = api("/v1/querybatch", {"queries": queries}, base).get("results", [])
        for offset, result in enumerate(results):
            if result.get("vulns"):
                hits[start + offset] = [v["id"] for v in result["vulns"]]
    cache = {}
    for ids in hits.values():
        for vuln_id in ids:
            if vuln_id not in cache and len(cache) < max_details:
                cache[vuln_id] = api(f"/v1/vulns/{quote(vuln_id)}", base=base)
    return {index: [summarise_vuln(cache[i], deps[index]) if i in cache
                    else {"id": i, "aliases": [], "summary": "(details not fetched)",
                          "severity": "unknown", "fixed": []} for i in ids]
            for index, ids in hits.items()}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check pinned dependencies against OSV.")
    parser.add_argument("file", type=Path,
                        help="requirements.txt, package.json or package-lock.json")
    parser.add_argument("--db", type=Path,
                        help="a saved advisory database (JSON) to use instead of the OSV website")
    parser.add_argument("--osv-url", help="another OSV-compatible server (default api.osv.dev)")
    parser.add_argument("--ignore", action="append", default=[], metavar="ID",
                        help="skip this advisory id (repeatable)")
    parser.add_argument("--fail-on", choices=["low", "moderate", "high", "critical"],
                        default="low", help="exit 1 if a finding is at least this serious (low)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)
    try:
        deps, skipped = read_dependencies(args.file)
        if not deps:
            print("No exactly pinned dependencies found to check.", file=sys.stderr)
            return 1
        if args.db:
            database = json.loads(args.db.read_text(encoding="utf-8"))
            hits = {i: found for i, d in enumerate(deps) if (found := from_db(database, d))}
        else:
            hits = from_osv(deps, args.osv_url)
    except (OSError, ValueError, KeyError, urllib.error.URLError) as err:
        print(f"Can't check the dependencies: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1

    ignored = set(args.ignore)
    findings = []
    for index, advisories in hits.items():
        for adv in advisories:
            if adv["id"] not in ignored and not ignored & set(adv["aliases"]):
                findings.append({"package": deps[index]["name"], "version": deps[index]["version"],
                                 **adv})
    findings.sort(key=lambda f: (-SEVERITY.get(f["severity"], 0), f["package"], f["id"]))
    if args.format == "json":
        print(json.dumps({"checked": len(deps), "skipped": skipped, "findings": findings},
                         indent=1))
    else:
        source = f"saved database {args.db.name}" if args.db else (args.osv_url or OSV_URL)
        print(f"Checked {len(deps)} pinned package(s) against {source}.")
        for f in findings:
            fix = f"fixed in {', '.join(f['fixed'])}" if f["fixed"] else "no fixed version listed"
            alias = f" ({', '.join(f['aliases'][:2])})" if f["aliases"] else ""
            print(f"\n[{f['severity'].upper()}] {f['package']}=={f['version']}: {f['id']}{alias}")
            print(f"    {f['summary']}\n    {fix}")
        if not findings:
            print("No known vulnerabilities found for those versions.")
        if skipped:
            print(f"\nNot checked ({len(skipped)}): " + "; ".join(skipped[:8])
                  + (" ..." if len(skipped) > 8 else ""))
    limit = SEVERITY[args.fail_on]
    bad = any(SEVERITY.get(f["severity"], 0) >= limit or f["severity"] == "unknown"
              for f in findings)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
