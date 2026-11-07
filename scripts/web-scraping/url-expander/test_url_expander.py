import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import url_expander as ue


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_HEAD(self):
        routes = {"/short": (301, "/mid"), "/mid": (302, "/final?utm_source=x&id=7"),
                  "/loop-a": (302, "/loop-b"), "/loop-b": (302, "/loop-a"),
                  "/gone": (404, None)}
        code, location = routes.get(self.path.split("?")[0], (200, None))
        if self.path.startswith("/final"):
            code, location = 200, None
        self.send_response(code)
        if location:
            self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_GET = do_HEAD


@pytest.fixture
def base():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_clean_url_removes_tracking_only():
    assert ue.clean_url("HTTPS://Example.COM/a?utm_source=x&id=7&fbclid=abc&q=hello+world") == (
        "https://example.com/a?id=7&q=hello+world")
    assert ue.clean_url("https://x.test/p#frag") == "https://x.test/p#frag"
    assert ue.clean_url("https://x.test/p?UTM_Medium=m&flag") == "https://x.test/p?flag="


def test_follow_chain_and_outcomes(base):
    chain, outcome = ue.follow(base + "/short")
    assert [status for _, status in chain] == [301, 302, 200] and outcome == "ok"
    assert chain[-1][0].endswith("/final?utm_source=x&id=7")
    assert ue.follow(base + "/gone")[1] == "ended with HTTP 404"
    assert ue.follow(base + "/loop-a")[1] == "redirect loop"
    assert ue.follow(base + "/short", max_hops=1)[1] == "stopped after 1 redirects"


def test_cli_cleans_final_url_and_shows_chain(base, capsys):
    assert ue.main([base + "/short", "--clean", "--chain"]) == 0
    out = capsys.readouterr().out
    assert f"-> {base}/final?id=7  [ok, 2 redirect(s)]" in out
    assert "301  " in out and "200  " in out


def test_cli_no_follow_makes_no_requests(capsys):
    assert ue.main(["http://Example.org/p?utm_source=a&id=1", "--no-follow", "--clean"]) == 0
    assert "-> http://example.org/p?id=1" in capsys.readouterr().out
    assert ue.main(["ftp://x.test/file", "--no-follow"]) == 1
    assert ue.main(["http://127.0.0.1:9/"]) == 1
    assert "ERROR" in capsys.readouterr().out


def test_exit_code_for_broken_target(base):
    assert ue.main([base + "/gone"]) == 1
