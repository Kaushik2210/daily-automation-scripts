"""Run smoke tests against REST endpoints described in a JSON file."""
import argparse
import json
import os
import re
import sys
import time
import urllib.error  # web-ok: the network is only used when running; --validate works offline
import urllib.request
from pathlib import Path

USER_AGENT = "daily-automation-scripts/1.0 (api smoke tester)"
KNOWN_KEYS = {"name", "method", "path", "url", "headers", "body", "expect_status", "expect_json",
              "expect_contains", "expect_header", "max_ms"}


def expand(value, missing):
    def replace(match):
        found = os.environ.get(match.group(1))
        if found is None:
            missing.add(match.group(1))
            return match.group(0)
        return found
    return re.sub(r"\$\{(\w+)\}", replace, value) if isinstance(value, str) else value


def validate_spec(spec):
    """Return (list of problems, list of normalised tests)."""
    problems, tests = [], []
    if not isinstance(spec, dict) or not isinstance(spec.get("tests"), list) or not spec["tests"]:
        return ["the file needs a non-empty 'tests' list"], []
    base = spec.get("base_url", "").rstrip("/")
    names = set()
    for number, test in enumerate(spec["tests"], 1):
        if not isinstance(test, dict):
            problems.append(f"test {number}: must be an object")
            continue
        name = test.get("name") or f"test {number}"
        label = f"'{name}'"
        if name in names:
            problems.append(f"{label}: the name is used twice")
        names.add(name)
        for key in test:
            if key not in KNOWN_KEYS:
                problems.append(f"{label}: unknown setting '{key}'")
        url = test.get("url") or base + test.get("path", "")
        if not url.startswith(("http://", "https://")):
            problems.append(f"{label}: needs a 'url', or a 'path' together with a base_url")
        if test.get("method", "GET").upper() not in ("GET", "POST", "PUT", "PATCH", "DELETE",
                                                        "HEAD", "OPTIONS"):
            problems.append(f"{label}: unknown method '{test.get('method')}'")
        status = test.get("expect_status", 200)
        if not isinstance(status, int) or not 100 <= status <= 599:
            problems.append(f"{label}: expect_status must be a status code such as 200")
        if "max_ms" in test and not isinstance(test["max_ms"], (int, float)):
            problems.append(f"{label}: max_ms must be a number")
        for key in ("expect_json", "expect_header"):
            if key in test and not isinstance(test[key], dict):
                problems.append(f"{label}: {key} must be an object")
        tests.append({**test, "name": name, "url": url})
    return problems, tests


def dig(data, dotted):
    """Follow 'a.b.0.c' through nested dicts and lists. Returns (found, value)."""
    for part in dotted.split("."):
        if isinstance(data, dict) and part in data:
            data = data[part]
        elif isinstance(data, list) and part.isdigit() and int(part) < len(data):
            data = data[int(part)]
        else:
            return False, None
    return True, data


def run_test(test, base_headers, timeout):
    """Run one test. Returns (list of failure messages, status, ms)."""
    missing = set()
    wanted = {**base_headers, **test.get("headers", {})}
    headers = {"User-Agent": USER_AGENT, **{k: expand(v, missing) for k, v in wanted.items()}}
    if missing:
        return [f"environment variable(s) not set: {', '.join(sorted(missing))}"], 0, 0
    body = None
    if test.get("body") is not None:
        body = json.dumps(test["body"]).encode()
        headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(test["url"], data=body, headers=headers,
                                     method=test.get("method", "GET").upper())
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status, raw, reply = response.status, response.read(2_000_000), response.headers
    except urllib.error.HTTPError as err:
        status, raw, reply = err.code, err.read(2_000_000), err.headers
    except (urllib.error.URLError, OSError, ValueError) as err:
        return [f"request failed: {getattr(err, 'reason', err)}"], 0, 0
    ms = round((time.perf_counter() - started) * 1000)
    failures, text = [], raw.decode("utf-8", errors="replace")
    expected = test.get("expect_status", 200)
    if status != expected:
        failures.append(f"status {status}, expected {expected}")
    if "max_ms" in test and ms > test["max_ms"]:
        failures.append(f"took {ms} ms, limit {test['max_ms']} ms")
    if "expect_contains" in test and test["expect_contains"] not in text:
        failures.append(f"body does not contain {test['expect_contains']!r}")
    for name, part in test.get("expect_header", {}).items():
        actual = reply.get(name)
        if actual is None or str(part).lower() not in actual.lower():
            failures.append(f"header {name} is {actual!r}, expected it to contain {part!r}")
    if test.get("expect_json"):
        try:
            data = json.loads(text)
        except ValueError:
            failures.append("body is not JSON")
        else:
            for path, want in test["expect_json"].items():
                found, value = dig(data, path)
                if not found:
                    failures.append(f"JSON field '{path}' is missing")
                elif want != "*" and value != want:
                    failures.append(f"JSON field '{path}' is {value!r}, expected {want!r}")
    return failures, status, ms


def main(argv=None):
    parser = argparse.ArgumentParser(description="Smoke-test REST endpoints from a JSON file.")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--base-url", help="use this base URL instead of the file's")
    parser.add_argument("--only", help="run only the test with this name")
    parser.add_argument("--fail-fast", action="store_true", help="stop at the first failure")
    parser.add_argument("--timeout", type=float, default=10, help="seconds per request (10)")
    parser.add_argument("--validate", action="store_true",
                        help="check the file and list the tests; make no requests")
    args = parser.parse_args(argv)
    if not args.spec.is_file():
        parser.error(f"not a file: {args.spec}")
    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        print(f"Can't read the test file: {err}", file=sys.stderr)
        return 1
    if args.base_url and isinstance(spec, dict):
        spec["base_url"] = args.base_url
    problems, tests = validate_spec(spec)
    for problem in problems:
        print(f"PROBLEM  {problem}")
    if problems:
        return 1
    if args.only:
        tests = [t for t in tests if t["name"] == args.only]
        if not tests:
            print(f"No test named '{args.only}'.", file=sys.stderr)
            return 1
    if args.validate:
        for test in tests:
            checks = [k.replace("expect_", "") for k in test if k.startswith("expect_")
                      or k == "max_ms"]
            print(f"ok  {test.get('method', 'GET'):<6} {test['name']:<22} {test['url']}  "
                  f"[{', '.join(checks) or 'status 200'}]")
        print(f"\n{len(tests)} test(s) look valid. No requests were made.")
        return 0

    failed = 0
    for test in tests:
        failures, status, ms = run_test(test, spec.get("headers", {}), args.timeout)
        verdict = "PASS" if not failures else "FAIL"
        print(f"{verdict}  {test.get('method', 'GET'):<6} {test['name']:<22} "
              f"{status or '---':>3} {ms:>5} ms")
        for message in failures:
            print(f"        - {message}")
        failed += bool(failures)
        if failures and args.fail_fast:
            break
    print(f"\n{len(tests) - failed} passed, {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
