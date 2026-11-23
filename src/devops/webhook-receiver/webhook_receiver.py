"""A local server that logs incoming webhooks, checks their signatures, and shows the log."""
import argparse
import hashlib
import hmac
import json
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # web-ok: only used by `serve`
from pathlib import Path

SENSITIVE = {"authorization", "cookie", "x-api-key", "proxy-authorization"}
SIGNATURE_HEADERS = ["x-hub-signature-256", "x-signature-256", "x-signature", "x-webhook-signature"]
MAX_BODY = 1_000_000


def sign(secret, body):
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def check_signature(secret, body, headers):
    """Return 'none' (no secret or no signature header), 'valid' or 'INVALID'."""
    if not secret:
        return "none"
    given = next((headers[h] for h in SIGNATURE_HEADERS if h in headers), None)
    if given is None:
        return "none"
    given = given.strip().removeprefix("sha256=")
    expected = sign(secret, body).removeprefix("sha256=")
    return "valid" if hmac.compare_digest(given.lower(), expected) else "INVALID"


def describe_body(body, content_type):
    """Parse a body for the log: JSON when it is JSON, text otherwise."""
    if not body:
        return None
    text = body.decode("utf-8", errors="replace")
    if "json" in content_type or text.lstrip().startswith(("{", "[")):
        try:
            return json.loads(text)
        except ValueError:
            pass
    return text


def make_entry(method, path, headers, body, secret):
    clean = {k.lower(): ("<redacted>" if k.lower() in SENSITIVE else v) for k, v in headers.items()}
    lowered = {k.lower(): v for k, v in headers.items()}
    return {"time": datetime.now().isoformat(timespec="seconds"), "method": method, "path": path,
            "headers": clean, "body": describe_body(body, lowered.get("content-type", "")),
            "signature": check_signature(secret, body, lowered), "size": len(body)}


def make_server(host, port, log, secret=None, status=200, reject_invalid=False, on_event=print,
                max_requests=0):
    """Build the HTTP server. It stops itself after max_requests requests when that is set."""
    state = {"count": 0}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def handle_any(self):
            size = min(int(self.headers.get("Content-Length") or 0), MAX_BODY)
            body = self.rfile.read(size) if size else b""
            entry = make_entry(self.command, self.path, dict(self.headers), body, secret)
            reply = 401 if reject_invalid and entry["signature"] == "INVALID" else status
            entry["responded"] = reply
            with log.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
            on_event(entry)
            answer = {"received": reply < 400, "signature": entry["signature"]}
            payload = json.dumps(answer).encode()
            self.send_response(reply)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            state["count"] += 1
            if max_requests and state["count"] >= max_requests:
                threading.Thread(target=self.server.shutdown, daemon=True).start()

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = handle_any

    return ThreadingHTTPServer((host, port), Handler)


def line_for(entry):
    body = entry.get("body")
    if body is None:
        preview = "(no body)"
    else:
        preview = json.dumps(body, ensure_ascii=False) if not isinstance(body, str) else body
    preview = preview.replace("\n", " ")
    preview = preview if len(preview) <= 50 else preview[:49] + "…"
    return (f"{entry['time'][11:]}  {entry['method']:<6} {entry['path']:<18} "
            f"{entry.get('signature', 'none'):<8} {entry.get('size', 0):>5} B  {preview}")


def read_log(path):
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entries.append(json.loads(line))
        except ValueError:
            continue
    return entries


def main(argv=None):
    parser = argparse.ArgumentParser(description="Receive, log and inspect webhooks.")
    parser.add_argument("action", choices=["serve", "show", "verify"])
    parser.add_argument("file", nargs="?", type=Path,
                        help="show: the log to read; verify: the saved payload")
    parser.add_argument("--log", type=Path, default=Path("webhook-log.jsonl"),
                        help="log file for serve (webhook-log.jsonl)")
    parser.add_argument("--host", default="127.0.0.1", help="address to listen on (127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="port to listen on (8000)")
    parser.add_argument("--secret", help="shared secret for HMAC SHA-256 signature checks")
    parser.add_argument("--signature", help="verify: the signature to check, e.g. sha256=ab12...")
    parser.add_argument("--status", type=int, default=200, help="status code to answer with (200)")
    parser.add_argument("--reject-invalid", action="store_true",
                        help="answer 401 when a signature is present but wrong")
    parser.add_argument("--max-requests", type=int, default=0, help="stop after this many requests")
    parser.add_argument("--path", help="show: only entries whose path contains this")
    parser.add_argument("--last", type=int, default=20, help="show: how many entries (20)")
    args = parser.parse_args(argv)

    if args.action == "verify":
        if not (args.file and args.secret and args.signature):
            parser.error("verify needs FILE, --secret and --signature")
        if not args.file.is_file():
            parser.error(f"not a file: {args.file}")
        body = args.file.read_bytes()
        expected = sign(args.secret, body)
        good = hmac.compare_digest(args.signature.strip().removeprefix("sha256=").lower(),
                                   expected.removeprefix("sha256="))
        print(f"Payload: {args.file.name} ({len(body)} bytes)\nExpected: {expected}\n"
              f"Given:    {args.signature.strip()}\nResult:   {'VALID' if good else 'INVALID'}")
        return 0 if good else 1

    if args.action == "show":
        if not args.file or not args.file.is_file():
            parser.error("show needs the log file, e.g. webhook-log.jsonl")
        entries = [e for e in read_log(args.file) if not args.path or args.path in e["path"]]
        for entry in entries[-args.last:]:
            print(line_for(entry))
        bad = sum(e.get("signature") == "INVALID" for e in entries)
        print(f"\n{len(entries)} request(s)" + (f", {bad} with an INVALID signature" if bad else "")
              + f"; showing the last {min(args.last, len(entries))}.")
        return 1 if bad else 0

    try:
        server = make_server(args.host, args.port, args.log, args.secret, args.status,
                             args.reject_invalid, lambda e: print(line_for(e), flush=True),
                             args.max_requests)
    except OSError as err:
        print(f"Can't listen on {args.host}:{args.port}: {err}", file=sys.stderr)
        return 1
    print(f"Listening on http://{args.host}:{server.server_address[1]}/  (log: {args.log}, "
          f"Ctrl-C to stop)")
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        print("Warning: this address can be reached from other computers.", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
