import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import broken_link_finder as bl
import pytest

PAGE = """<a href="/ok">ok</a> <a href="/gone">gone</a> <a href="#top">top</a>
<a href="mailto:x@y.test">mail</a> <a href="/ok#again">ok again</a>
<a href="https://other.invalid/zzz">other</a> <a href="/noindexhead">head refused</a>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self, code):
        self.send_response(code)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self):
        self.respond(405 if self.path == "/noindexhead" else (200 if self.path == "/ok" else 404))

    def do_GET(self):
        self.respond(200 if self.path in ("/ok", "/noindexhead") else 404)


@pytest.fixture
def base():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_links_on_page_resolves_dedupes_and_skips():
    links = bl.links_on_page(PAGE, "https://site.test/dir/")
    assert links == ["https://site.test/ok", "https://site.test/gone", "https://other.invalid/zzz",
                     "https://site.test/noindexhead"]


def test_internal_check():
    assert bl.is_internal("https://Site.test/a", "https://site.test/")
    assert not bl.is_internal("https://other.test/a", "https://site.test/")


def test_check_statuses(base):
    assert bl.check(base + "/ok") == (200, "")
    assert bl.check(base + "/gone") == (404, "")
    assert bl.check(base + "/noindexhead") == (200, "")        # HEAD refused, GET works
    status, error = bl.check("http://127.0.0.1:9/", timeout=2)
    assert status is None and error


def test_plan_makes_no_requests(tmp_path, capsys):
    f = tmp_path / "p.html"
    f.write_text(PAGE)
    assert bl.main([str(f), "--base", "https://site.test/", "--plan"]) == 0
    out = capsys.readouterr().out
    assert "Would check 4 link(s)" in out and "WOULD CHECK  https://site.test/gone" in out
    assert bl.main([str(f), "--base", "https://site.test/", "--plan", "--only", "external"]) == 0
    assert "Would check 1 link(s)" in capsys.readouterr().out


def test_full_run_reports_broken_links(base, tmp_path, capsys):
    f = tmp_path / "p.html"
    f.write_text('<a href="/ok">a</a><a href="/gone">b</a><a href="/noindexhead">c</a>')
    assert bl.main([str(f), "--base", base + "/"]) == 1
    out = capsys.readouterr().out
    assert f"BROKEN  404  {base}/gone" in out and "3 link(s) checked, 1 broken." in out
    f.write_text('<a href="/ok">a</a>')
    assert bl.main([str(f), "--base", base + "/"]) == 0


def test_file_needs_base_and_max_limit(tmp_path, capsys):
    f = tmp_path / "p.html"
    f.write_text(PAGE)
    with pytest.raises(SystemExit):
        bl.main([str(f)])
    bl.main([str(f), "--base", "https://site.test/", "--plan", "--max", "2"])
    assert "Would check 2 link(s)" in capsys.readouterr().out
