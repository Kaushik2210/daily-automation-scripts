import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import bulk_url_checker as bu
import pytest


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self, code, location=None):
        self.send_response(code)
        if location:
            self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self):
        if self.path == "/nohead":
            return self.respond(405)
        self.route()

    def do_GET(self):
        self.route()

    def route(self):
        if self.path in ("/ok", "/nohead"):
            self.respond(200)
        elif self.path == "/redirect":
            self.respond(302, "/ok")
        else:
            self.respond(404)


@pytest.fixture
def base():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_normalize_and_validation():
    assert bu.normalize("HTTPS://Example.COM#top") == "https://example.com/"
    assert bu.normalize("https://example.com/a?x=1") == "https://example.com/a?x=1"
    assert bu.is_http_url("https://example.com") and not bu.is_http_url("ftp://x.test")
    assert not bu.is_http_url("not a url") and not bu.is_http_url("https://")


def test_plan_dedupes_and_flags_invalid():
    urls, invalid, dupes = bu.plan(["https://a.test", "https://A.test/", "junk", "https://b.test"])
    assert urls == ["https://a.test/", "https://b.test/"] and invalid == ["junk"] and dupes == 1


def test_read_inputs_from_file_and_args(tmp_path):
    f = tmp_path / "urls.txt"
    f.write_text("# comment\nhttps://a.test\n\nhttps://b.test\n")
    assert bu.read_inputs([str(f), "https://c.test"]) == [
        "https://a.test", "https://b.test", "https://c.test"]


def test_check_url_statuses(base):
    assert bu.check_url(base + "/ok")["status"] == 200
    assert bu.check_url(base + "/missing")["status"] == 404
    redirect = bu.check_url(base + "/redirect")
    assert redirect["status"] == 200 and redirect["final"].endswith("/ok")
    assert bu.check_url(base + "/nohead")["status"] == 200        # HEAD refused, GET works


def test_connection_error_is_reported_not_raised():
    result = bu.check_url("http://127.0.0.1:9/", timeout=2)
    assert result["status"] is None and result["error"]
    assert not bu.is_ok(result)


def test_cli_plan_and_real_run(base, capsys):
    assert bu.main([base + "/ok", base + "/ok", "--plan"]) == 0
    assert "Would check 1 URL(s); 0 invalid, 1 duplicate(s) removed." in capsys.readouterr().out
    assert bu.main([base + "/ok", base + "/redirect"]) == 0
    assert "2 checked, 2 ok, 0 broken." in capsys.readouterr().out
    assert bu.main([base + "/ok", base + "/missing"]) == 1
    assert "FAIL 404" in capsys.readouterr().out
