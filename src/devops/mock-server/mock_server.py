"""Serve mock API responses from a JSON file, or preview what a request would get."""
import argparse
import json
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # web-ok: only used by `serve`
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "*"}
PLACEHOLDER = re.compile(r"\{([\w.]+)\}")


def validate(definition):
    """Return (list of problems, normalised routes)."""
    problems, routes = [], []
    if not isinstance(definition, dict) or not isinstance(definition.get("routes"), list):
        return ["the file needs a 'routes' list"], []
    seen = set()
    for number, route in enumerate(definition["routes"], 1):
        if not isinstance(route, dict):
            problems.append(f"route {number}: must be an object")
            continue
        method = str(route.get("method", "GET")).upper()
        path = route.get("path", "")
        label = f"route {number} ({method} {path})"
        if method not in METHODS:
            problems.append(f"{label}: unknown method")
        if not isinstance(path, str) or not path.startswith("/"):
            problems.append(f"{label}: the path must start with /")
        status = route.get("status", 200)
        if not isinstance(status, int) or not 100 <= status <= 599:
            problems.append(f"{label}: status must be a code such as 200")
        if not isinstance(route.get("delay_ms", 0), (int, float)) or route.get("delay_ms", 0) < 0:
            problems.append(f"{label}: delay_ms must be a positive number")
        if not isinstance(route.get("headers", {}), dict):
            problems.append(f"{label}: headers must be an object")
        if (method, path) in seen:
            problems.append(f"{label}: defined twice (the first one wins)")
        seen.add((method, path))
        routes.append({**route, "method": method, "path": path, "status": status})
    return problems, routes


def compile_path(path):
    names = []

    def piece(match):
        names.append(match.group(1))
        return "([^/]+)"
    regex = PLACEHOLDER.sub(piece, re.escape(path).replace(r"\{", "{").replace(r"\}", "}"))
    return re.compile(f"^{regex}/?$"), names


def find_route(routes, method, path):
    """Return (route, path params) for the first route matching, else (None, {})."""
    for route in routes:
        if route["method"] not in (method.upper(), "*"):
            continue
        regex, names = compile_path(route["path"])
        match = regex.match(path)
        if match:
            return route, dict(zip(names, match.groups(), strict=True))
    return None, {}


def fill(value, values):
    """Replace {name} placeholders in every string of a JSON value."""
    if isinstance(value, str):
        return PLACEHOLDER.sub(lambda m: str(values.get(m.group(1), m.group(0))), value)
    if isinstance(value, list):
        return [fill(v, values) for v in value]
    if isinstance(value, dict):
        return {k: fill(v, values) for k, v in value.items()}
    return value


def build_response(routes, method, target):
    """Return (status, headers, body bytes, delay seconds) for a request like 'GET /users/3?x=1'."""
    parts = urlsplit(target)
    query = {f"query.{k}": v[0] for k, v in parse_qs(parts.query).items()}
    route, params = find_route(routes, method, parts.path)
    if route is None:
        known = [f"{r['method']} {r['path']}" for r in routes]
        body = json.dumps({"error": f"no mock for {method.upper()} {parts.path}",
                           "routes": known}).encode()
        return 404, {"Content-Type": "application/json"}, body, 0.0
    values = {**params, **query}
    body = fill(route.get("body"), values)
    headers = {k: str(fill(v, values)) for k, v in route.get("headers", {}).items()}
    if isinstance(body, (dict, list)):
        headers.setdefault("Content-Type", "application/json")
        data = json.dumps(body).encode()
    else:
        headers.setdefault("Content-Type", "text/plain; charset=utf-8")
        data = b"" if body is None else str(body).encode()
    return route["status"], headers, data, float(route.get("delay_ms", 0)) / 1000


def make_server(host, port, routes, cors=True, on_request=print, sleep=time.sleep):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def handle_any(self):
            size = int(self.headers.get("Content-Length") or 0)
            if size:
                self.rfile.read(min(size, 1_000_000))
            if cors and self.command == "OPTIONS":
                status, headers, data, delay = 204, {}, b"", 0.0
            else:
                status, headers, data, delay = build_response(routes, self.command, self.path)
            if delay:
                sleep(delay)
            if cors:
                headers = {"Access-Control-Allow-Origin": "*",
                           "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
                           "Access-Control-Allow-Headers": "*", **headers}
            on_request(f"{self.command:<6} {self.path:<30} -> {status}"
                       + (f" (after {delay:g}s)" if delay else ""))
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = handle_any

    return ThreadingHTTPServer((host, port), Handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Serve mock API responses from a JSON file.")
    parser.add_argument("action", choices=["serve", "check", "simulate"])
    parser.add_argument("definition", type=Path, help="the JSON file describing the routes")
    parser.add_argument("request", nargs="?", help="simulate: e.g. 'GET /users/3?x=1'")
    parser.add_argument("--host", default="127.0.0.1", help="address to listen on (127.0.0.1)")
    parser.add_argument("--port", type=int, help="port to listen on (the file's, or 8080)")
    parser.add_argument("--no-cors", action="store_true", help="don't add CORS headers")
    parser.add_argument("--max-requests", type=int, default=0, help="stop after this many requests")
    args = parser.parse_args(argv)
    if not args.definition.is_file():
        parser.error(f"not a file: {args.definition}")
    try:
        definition = json.loads(args.definition.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        print(f"Can't read the definition: {err}", file=sys.stderr)
        return 1
    problems, routes = validate(definition)
    for problem in problems:
        print(f"PROBLEM  {problem}")
    if problems:
        return 1

    if args.action == "check":
        for route in routes:
            note = f"  (delay {route['delay_ms']} ms)" if route.get("delay_ms") else ""
            print(f"{route['method']:<6} {route['path']:<22} -> {route['status']}{note}")
        port = args.port or definition.get("port", 8080)
        print(f"\n{len(routes)} route(s) look valid; the server would listen on port {port}.")
        return 0
    if args.action == "simulate":
        method, _, target = (args.request or "").partition(" ")
        if not target.startswith("/"):
            parser.error("simulate needs a request like 'GET /users/3'")
        status, headers, data, delay = build_response(routes, method, target.strip())
        print(f"HTTP {status}" + (f"  (the real server would wait {delay:g}s)" if delay else ""))
        for name, value in headers.items():
            print(f"{name}: {value}")
        print()
        print(data.decode("utf-8"))
        return 0 if status < 400 else 1

    port = args.port if args.port is not None else definition.get("port", 8080)
    count = [0]

    def log(line):
        print(line, flush=True)
        count[0] += 1
        if args.max_requests and count[0] >= args.max_requests:
            threading.Thread(target=server.shutdown, daemon=True).start()
    try:
        server = make_server(args.host, port, routes, not args.no_cors, log)
    except OSError as err:
        print(f"Can't listen on {args.host}:{port}: {err}", file=sys.stderr)
        return 1
    address = f"http://{args.host}:{server.server_address[1]}/"
    print(f"Mock server for {len(routes)} route(s) on {address} (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
