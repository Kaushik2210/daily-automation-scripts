import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import header_inspector as hi
import pytest

RAW = """HTTP/2 200
content-type: text/html; charset=utf-8
Server: nginx/1.24
cache-control: public, max-age=3600
content-length: 18211
x-powered-by: Express
set-cookie: a=1; HttpOnly
set-cookie: b=2

HTTP/2 999
ignored: second response
"""


def test_parse_headers_lowercases_keeps_repeats_and_stops_at_blank_line():
    status, headers = hi.parse_headers(RAW)
    assert status == "HTTP/2 200"
    assert [n for n, _ in headers].count("set-cookie") == 2
    assert ("server", "nginx/1.24") in headers and not any(n == "ignored" for n, _ in headers)


def test_human_formatting():
    assert hi.human_duration(3600) == "1 hour" and hi.human_duration(172800) == "2 days"
    assert hi.human_duration(5) == "5 seconds" and hi.human_duration(60) == "1 minute"
    assert hi.human_size(18211) == "17.8 KB" and hi.human_size(12) == "12 bytes"


def test_notes():
    notes = hi.notes_for(hi.parse_headers(RAW)[1])
    assert "Content: text/html (17.8 KB)" in notes
    assert "Caching: reusable for 1 hour" in notes
    assert "Technology revealed by X-Powered-By: Express" in notes
    assert "Sets 2 cookies" in notes and "No HSTS header" in notes
    assert "Caching: not stored (no-store)" in hi.notes_for([("cache-control", "no-store")])
    assert "Redirects to: /next" in hi.notes_for([("location", "/next")])


def test_cli_with_saved_dump(tmp_path, capsys):
    f = tmp_path / "headers.txt"
    f.write_text(RAW)
    assert hi.main([str(f)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("HTTP/2 200") and "Notes:" in out
    empty = tmp_path / "empty.txt"
    empty.write_text("nothing here")
    assert hi.main([str(empty)]) == 1
    with pytest.raises(SystemExit):
        hi.main([str(tmp_path / "missing.txt")])


def test_live_request_against_a_local_server(capsys):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_HEAD(self):
            if self.path == "/old":
                self.send_response(301)
                self.send_header("Location", "/new")
            else:
                self.send_response(200)
                self.send_header("X-Demo", "yes")
            self.send_header("Content-Length", "0")
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        assert hi.main([base + "/old"]) == 0
        out = capsys.readouterr().out
        assert "301" in out and "Redirects to: /new" in out
        assert hi.main([base + "/old", "--follow"]) == 0
        assert "x-demo" in capsys.readouterr().out
    finally:
        server.shutdown()
