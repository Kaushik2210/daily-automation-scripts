"""Local web dashboard: browse the scripts, fill in a form and run them.

Runs on 127.0.0.1 only. Every script is started as a normal subprocess with an
argument list, never through a shell.
"""
import argparse
import ast
import json
import os
import secrets
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
STATIC = HERE / "static"
MAX_OUTPUT = 200_000
MAX_BODY = 1_000_000
RUN_TIMEOUT = 120
ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
}
CSP = (
    "default-src 'self'; script-src 'self'; "
    "style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com"
)
_SCHEMAS = {}


def summary_of(path):
    try:
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
    except (OSError, SyntaxError):
        return ""
    return doc.splitlines()[0] if doc else ""


def discover(root=ROOT):
    """Return {id: info} for every scripts/<category>/<name>/<name_with_underscores>.py."""
    found = {}
    for path in sorted((Path(root) / "scripts").glob("*/*/*.py")):
        name, category = path.parent.name, path.parent.parent.name
        if path.stem == name.replace("-", "_"):
            found[f"{category}/{name}"] = {
                "id": f"{category}/{name}",
                "name": name,
                "category": category,
                "summary": summary_of(path),
                "path": path,
            }
    return found


def readme_sections(folder):
    readme = Path(folder) / "README.md"
    if not readme.is_file():
        return {}
    sections, current = {}, None
    for line in readme.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif current:
            sections[current].append(line)
    return {title: "\n".join(lines).strip() for title, lines in sections.items()}


def get_schema(path):
    key = (str(path), path.stat().st_mtime_ns)
    if key not in _SCHEMAS:
        try:
            proc = subprocess.run(
                [sys.executable, str(HERE / "introspect.py"), str(path)],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
            )
            _SCHEMAS[key] = json.loads(proc.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            _SCHEMAS[key] = {"error": "Could not read this tool's options."}
    return _SCHEMAS[key]


def build_argv(arguments, values):
    """Turn form values into an argument list, checking them against the script's options."""
    known = {a["dest"] for a in arguments}
    unknown = set(values) - known
    if unknown:
        raise ValueError(f"Unknown option: {', '.join(sorted(unknown))}")
    options, positionals = [], []
    for arg in arguments:
        value = values.get(arg["dest"])
        items = value if isinstance(value, list) else [value]
        items = [str(i) for i in items if i not in (None, "", False)]
        if arg["positional"]:
            if arg["required"] and not items:
                raise ValueError(f"{arg['metavar'] or arg['dest']} is required")
            positionals.extend(items)
            continue
        flag = max(arg["flags"], key=len)
        if arg["kind"] == "flag":
            if value is True:
                options.append(flag)
            continue
        if arg["required"] and not items:
            raise ValueError(f"{flag} is required")
        if arg["kind"] == "multi" and arg["nargs"]:
            if items:
                options += [flag, *items]
        else:
            for item in items:
                options += [flag, item]
    return options + (["--", *positionals] if positionals else [])


def run_script(path, argv, stdin_text="", timeout=RUN_TIMEOUT):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    started = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, str(path), *argv], input=stdin_text, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=timeout, env=env,
            cwd=Path.home(),
        )
        result = {"exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr,
                  "timed_out": False}
    except subprocess.TimeoutExpired as err:
        out = err.stdout.decode("utf-8", "replace") if isinstance(err.stdout, bytes) else ""
        result = {"exit_code": None, "stdout": out or "", "stderr": "", "timed_out": True}
    for key in ("stdout", "stderr"):
        if len(result[key]) > MAX_OUTPUT:
            result[key] = result[key][:MAX_OUTPUT] + "\n... output truncated"
    result["seconds"] = round(time.monotonic() - started, 2)
    return result


def render_index(token):
    page = (STATIC / "index.html").read_text(encoding="utf-8")
    for key, value in {"__TOKEN__": token, "__MODE__": "server", "__ROOT__": "./",
                       "__TOOL__": ""}.items():
        page = page.replace(key, value)
    return page.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_body(self, status, body, content_type="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", CSP)
        self.end_headers()
        self.wfile.write(data)

    def host_ok(self):
        return urlparse("//" + self.headers.get("Host", "")).hostname in ALLOWED_HOSTS

    def do_GET(self):
        if not self.host_ok():
            return self.send_body(403, {"error": "Forbidden host"})
        path = urlparse(self.path).path
        if path == "/":
            return self.send_body(200, render_index(self.server.token), CONTENT_TYPES[".html"])
        if path in ("/static/app.css", "/static/app.js"):
            file = STATIC / path.rsplit("/", 1)[1]
            return self.send_body(200, file.read_bytes(), CONTENT_TYPES[file.suffix])
        scripts = discover(self.server.root)
        if path == "/api/scripts":
            listing = [{k: v for k, v in s.items() if k != "path"} for s in scripts.values()]
            return self.send_body(200, {"scripts": listing, "cwd": str(Path.home())})
        if path.startswith("/api/scripts/"):
            info = scripts.get(path.removeprefix("/api/scripts/"))
            if info:
                detail = {k: v for k, v in info.items() if k != "path"}
                detail["sections"] = readme_sections(info["path"].parent)
                detail["schema"] = get_schema(info["path"])
                return self.send_body(200, detail)
        return self.send_body(404, {"error": "Not found"})

    def do_POST(self):
        if not self.host_ok():
            return self.send_body(403, {"error": "Forbidden host"})
        if urlparse(self.path).path != "/api/run":
            return self.send_body(404, {"error": "Not found"})
        token = self.headers.get("X-Dashboard-Token", "")
        if not secrets.compare_digest(token, self.server.token):
            return self.send_body(403, {"error": "Missing or wrong token. Reload the page."})
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return self.send_body(413, {"error": "Request too large"})
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            info = discover(self.server.root).get(payload.get("script"))
            if info is None:
                return self.send_body(404, {"error": "Unknown tool"})
            schema = get_schema(info["path"])
            if "error" in schema:
                return self.send_body(400, {"error": schema["error"]})
            argv = build_argv(schema["arguments"], payload.get("values") or {})
        except (ValueError, json.JSONDecodeError, AttributeError) as err:
            return self.send_body(400, {"error": str(err)})
        stdin_text = str(payload.get("stdin") or "")
        return self.send_body(200, run_script(info["path"], argv, stdin_text))


def make_server(port=8765, root=ROOT):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.token = secrets.token_urlsafe(24)
    server.root = Path(root)
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description="Start the local web dashboard.")
    parser.add_argument("--port", type=int, default=8765, help="port to listen on")
    parser.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    args = parser.parse_args(argv)

    server = make_server(args.port)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Dashboard running at {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(0.5, webbrowser.open, args=[url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
