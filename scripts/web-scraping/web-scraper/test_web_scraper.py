import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import web_scraper as ws

HTML = """<html><body>
<h1 id="top">Shop</h1>
<ul class="items"><li class="item sale"><a href="/a">Alpha</a> <b>$5</b></li>
<li class="item"><a href="/b" data-sku="X-2">Beta</a> <b>$7</b></li></ul>
<div><p>Outside <a href="/c">Gamma</a></p></div>
<script>var hidden = "no";</script>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        bodies = {"/robots.txt": "User-agent: *\nDisallow: /private\n",
                  "/page": HTML, "/private/page": HTML}
        body = bodies.get(self.path)
        self.send_response(200 if body is not None else 404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write((body or "").encode())


@pytest.fixture
def base():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_selectors_tag_class_id_attribute_and_combinators():
    root = ws.parse_html(HTML)
    assert ws.extract(root, "h1") == ["Shop"]
    assert ws.extract(root, "#top") == ["Shop"]
    assert ws.extract(root, "li.item b") == ["$5", "$7"]
    assert ws.extract(root, "li.sale a") == ["Alpha"]
    assert ws.extract(root, "ul > li > a") == ["Alpha", "Beta"]
    assert ws.extract(root, "div > a") == []  # <a> is nested inside <p>, not a direct child
    assert ws.extract(root, "a[data-sku^=X]") == ["Beta"]
    assert ws.extract(root, "h1, .sale a") == ["Shop", "Alpha"]


def test_text_skips_scripts_and_attr_resolves_links():
    root = ws.parse_html(HTML)
    assert "hidden" not in ws.extract(root, "body")[0]
    assert ws.extract(root, "li a", attr="href", base="https://x.test/shop/") == [
        "https://x.test/a", "https://x.test/b"]
    assert ws.extract(root, "a", attr="data-sku") == ["X-2"]


def test_bad_selector_is_rejected():
    with pytest.raises(ValueError):
        ws.parse_selector("> a")


def test_cli_formats_for_a_saved_file(tmp_path, capsys):
    page = tmp_path / "shop.html"
    page.write_text(HTML)
    assert ws.main([str(page), "-s", "name=li a", "-s", "price=li b", "--format", "csv"]) == 0
    assert capsys.readouterr().out.splitlines() == ["name,price", "Alpha,$5", "Beta,$7"]
    assert ws.main([str(page), "-s", "li a", "--format", "json", "--limit", "1"]) == 0
    assert json.loads(capsys.readouterr().out) == {"selector1": ["Alpha"]}
    assert ws.main([str(page), "-s", "table"]) == 1


def test_robots_blocks_disallowed_paths(base, capsys):
    assert ws.main([base + "/page", "-s", "h1"]) == 0
    assert "[selector1] Shop" in capsys.readouterr().out
    assert ws.main([base + "/private/page", "-s", "h1"]) == 2
    assert "robots.txt asks bots not to fetch" in capsys.readouterr().out


def test_robots_file_overrides_the_live_check(base, tmp_path, capsys):
    robots = tmp_path / "robots.txt"
    robots.write_text("User-agent: *\nDisallow: /page\n")
    assert ws.main([base + "/page", "-s", "h1", "--robots-file", str(robots)]) == 2
    robots.write_text("User-agent: *\nDisallow:\n")
    assert ws.main([base + "/page", "-s", "h1", "--robots-file", str(robots)]) == 0
