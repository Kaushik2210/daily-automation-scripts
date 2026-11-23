"""Record API responses to JSON fixture files that tests can replay."""
import argparse
import contextlib
import json
import os
import re
import sys
import time
import urllib.error  # web-ok: the network is only used with --apply; the plan works offline
import urllib.request
from datetime import datetime
from pathlib import Path

with contextlib.suppress(ImportError):  # YAML specs are optional
    import yaml

SENSITIVE = {"authorization", "cookie", "set-cookie", "x-api-key", "proxy-authorization",
             "x-auth-token"}
USER_AGENT = "daily-automation-scripts/1.0 (api recorder)"


def expand(value, missing):
    """Replace ${NAME} with environment variables, collecting the names that aren't set."""
    def replace(match):
        found = os.environ.get(match.group(1))
        if found is None:
            missing.add(match.group(1))
            return match.group(0)
        return found
    return re.sub(r"\$\{(\w+)\}", replace, value) if isinstance(value, str) else value


def load_spec(path):
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yml", ".yaml"):
        if "yaml" not in globals():
            raise ValueError("reading YAML needs PyYAML (pip install pyyaml), or use a .json spec")
        spec = yaml.safe_load(text)
    else:
        spec = json.loads(text)
    if not isinstance(spec, dict) or not isinstance(spec.get("calls"), list):
        raise ValueError("the spec needs a 'calls' list")
    return spec


def build_calls(spec):
    """Turn the spec into [{name, method, url, headers, body}] and the set of missing variables."""
    missing, calls, names = set(), [], set()
    base = spec.get("base_url", "").rstrip("/")
    for number, call in enumerate(spec["calls"], 1):
        name = call.get("name") or f"call-{number}"
        if not re.fullmatch(r"[\w.-]+", name):
            raise ValueError(f"call name '{name}' may only use letters, digits, '.', '_' and '-'")
        if name in names:
            raise ValueError(f"call name '{name}' is used twice")
        names.add(name)
        url = call.get("url") or (base + call.get("path", ""))
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"call '{name}' needs a full 'url' or a 'path' with a base_url")
        headers = {**spec.get("headers", {}), **call.get("headers", {})}
        calls.append({"name": name, "method": call.get("method", "GET").upper(),
                      "url": expand(url, missing),
                      "headers": {k: expand(v, missing) for k, v in headers.items()},
                      "body": call.get("body")})
    return calls, missing


def redact(headers):
    return {k.lower(): ("<redacted>" if k.lower() in SENSITIVE else v) for k, v in headers.items()}


def record(call, timeout):
    """Make the request and return a fixture dict."""
    body = json.dumps(call["body"]).encode() if call["body"] is not None else None
    headers = {"User-Agent": USER_AGENT, **call["headers"]}
    if body is not None:
        headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(call["url"], data=body, method=call["method"],
                                     headers=headers)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status, raw, reply = response.status, response.read(2_000_000), dict(response.headers)
    except urllib.error.HTTPError as err:
        status, raw, reply = err.code, err.read(2_000_000), dict(err.headers)
    ms = round((time.perf_counter() - started) * 1000)
    text = raw.decode("utf-8", errors="replace")
    result = {"status": status, "ms": ms, "headers": redact(reply)}
    try:
        result["json"] = json.loads(text)
    except ValueError:
        result["text"] = text
    return {"request": {"method": call["method"], "url": call["url"],
                        "headers": redact(call["headers"]),
                        **({"body": call["body"]} if call["body"] is not None else {})},
            "response": result, "recorded_at": datetime.now().isoformat(timespec="seconds")}


def summarise_fixture(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    request, response = data.get("request", {}), data.get("response", {})
    kind = "json" if "json" in response else "text"
    return (path.stem, request.get("method", "?"), request.get("url", "?"),
            response.get("status", "?"), response.get("ms", "?"), kind,
            data.get("recorded_at", ""))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Record API responses as JSON fixtures.")
    parser.add_argument("spec", type=Path, nargs="?", help="spec file (JSON or YAML) of calls")
    parser.add_argument("-o", "--outdir", type=Path, default=Path("fixtures"),
                        help="folder for the fixtures (fixtures)")
    parser.add_argument("--only", help="record only the call with this name")
    parser.add_argument("--refresh", action="store_true", help="replace existing fixtures")
    parser.add_argument("--timeout", type=float, default=15, help="seconds per request (15)")
    parser.add_argument("--list", action="store_true",
                        help="list the fixtures already recorded in the output folder")
    parser.add_argument("--apply", action="store_true",
                        help="really call the API and write fixtures (default is a plan)")
    args = parser.parse_args(argv)

    if args.list:
        files = sorted(args.outdir.glob("*.json")) if args.outdir.is_dir() else []
        for path in files:
            try:
                name, method, url, status, ms, kind, when = summarise_fixture(path)
            except (OSError, ValueError):
                print(f"{path.stem:<20} unreadable fixture")
                continue
            print(f"{name:<20} {method:<6} {status!s:>3} {ms!s:>5} ms  {kind:<4} {url}  {when}")
        print(f"\n{len(files)} fixture(s) in {args.outdir}.")
        return 0 if files else 1
    if not args.spec:
        parser.error("give a spec file, or --list")
    if not args.spec.is_file():
        parser.error(f"not a file: {args.spec}")
    try:
        calls, missing = build_calls(load_spec(args.spec))
    except (OSError, ValueError) as err:
        print(f"Can't use the spec: {err}", file=sys.stderr)
        return 1
    if args.only:
        calls = [c for c in calls if c["name"] == args.only]
        if not calls:
            print(f"No call named '{args.only}'.", file=sys.stderr)
            return 1
    if missing and args.apply:
        print("Set these environment variables first: " + ", ".join(sorted(missing)),
              file=sys.stderr)
        return 1

    recorded = failed = skipped = 0
    for call in calls:
        target = args.outdir / f"{call['name']}.json"
        exists = target.exists()
        note = "exists, kept" if exists and not args.refresh else (
            "will be replaced" if exists else "new")
        print(f"{call['name']:<20} {call['method']:<6} {call['url']}  [{note}]")
        if exists and not args.refresh:
            skipped += 1
            continue
        if not args.apply:
            continue
        try:
            fixture = record(call, args.timeout)
        except (urllib.error.URLError, OSError, ValueError) as err:
            print(f"   FAILED: {getattr(err, 'reason', err)}")
            failed += 1
            continue
        args.outdir.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(fixture, indent=1, ensure_ascii=False) + "\n",
                          encoding="utf-8")
        recorded += 1
        print(f"   saved ({fixture['response']['status']}, {fixture['response']['ms']} ms)")
    if missing:
        names = ", ".join(sorted(missing))
        print(f"\nNote: variables not set here: {names} (needed with --apply).")
    if not args.apply:
        print(f"\nPlan only: {len(calls) - skipped} call(s) would be recorded into {args.outdir}. "
              "Use --apply to do it.")
        return 0
    print(f"\n{recorded} recorded, {skipped} kept, {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
