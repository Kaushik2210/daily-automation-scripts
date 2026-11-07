import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import link_extractor as le
import pytest

PAGE = """<html><body>
<a href="/products">Products</a> <a href="about.html">About <b>us</b></a>
<a href="https://other.test/x#frag">Other</a> <a href="#top">Top</a>
<a href="mailto:a@b.test">Mail</a> <a href="javascript:void(0)">JS</a>
<a href="/products">Products again</a>
<a href="https://partner.test/p" rel="nofollow noopener">Partner</a>
</body></html>"""


def test_extract_resolves_dedupes_and_classifies():
    links = le.extract_links(PAGE, "https://site.test/home/")
    assert [link["url"] for link in links] == [
        "https://site.test/products", "https://site.test/home/about.html",
        "https://other.test/x", "https://partner.test/p"]
    assert [link["kind"] for link in links] == ["internal", "internal", "external", "external"]
    assert links[1]["text"] == "About us"                       # nested tags are flattened
    assert links[3]["nofollow"] is True and links[0]["nofollow"] is False


def test_without_base_relative_links_stay_relative_and_absolute_are_external():
    links = le.extract_links(PAGE)
    assert links[0]["url"] == "/products" and links[0]["kind"] == "internal"
    assert links[2]["kind"] == "external"


def test_cli_with_saved_file_and_filter(tmp_path, capsys):
    f = tmp_path / "page.html"
    f.write_text(PAGE, encoding="utf-8")
    assert le.main([str(f), "--base", "https://site.test/"]) == 0
    out = capsys.readouterr().out
    assert "4 unique link(s): 2 internal, 2 external." in out
    le.main([str(f), "--base", "https://site.test/", "--only", "external"])
    out = capsys.readouterr().out
    assert "site.test/products" not in out and "2 unique link(s)" in out


def test_cli_fetches_from_a_local_server(capsys):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            body = b'<a href="/next">Next</a>'
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/start"
        assert le.main([url]) == 0
        assert f"http://127.0.0.1:{server.server_address[1]}/next" in capsys.readouterr().out
    finally:
        server.shutdown()


def test_errors(tmp_path, capsys):
    assert le.main(["http://127.0.0.1:9/"]) == 1
    assert "Couldn't load" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        le.main([str(tmp_path / "missing.html")])
