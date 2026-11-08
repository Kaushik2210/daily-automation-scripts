import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import image_downloader as idl
import pytest

PAGE = """<meta property="og:image" content="https://cdn.test/cover.jpg">
<img src="/a.jpg"><img src="b.png"><img data-src="/lazy.webp" src="placeholder.gif">
<img src="/small.jpg" srcset="/small.jpg 480w, /big.jpg 1600w">
<picture><source srcset="/wide.avif 2x, /wider.avif 3x"><img src="/fallback.jpg"></picture>
<img src="data:image/gif;base64,AAAA"><img src="/a.jpg">"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        routes = {"/img/one.png": ("image/png", b"\x89PNG-one"), "/img/two": ("image/jpeg", b"jpg"),
                  "/page.txt": ("text/plain", b"not an image")}
        kind, body = routes.get(self.path, (None, b""))
        self.send_response(200 if kind else 404)
        if kind:
            self.send_header("Content-Type", kind)
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture
def base():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_best_from_srcset_prefers_the_largest():
    assert idl.best_from_srcset("a.jpg 480w, b.jpg 1600w, c.jpg 800w") == "b.jpg"
    assert idl.best_from_srcset("a.jpg 1x, b.jpg 2x") == "b.jpg"
    assert idl.best_from_srcset("only.jpg") == "only.jpg"
    assert idl.best_from_srcset("") == ""


def test_find_images_resolves_dedupes_and_skips_data_uris():
    found = idl.find_images(PAGE, "https://x.test/shop/")
    assert found == [
        "https://cdn.test/cover.jpg", "https://x.test/a.jpg", "https://x.test/shop/b.png",
        "https://x.test/lazy.webp", "https://x.test/big.jpg", "https://x.test/wider.avif",
        "https://x.test/fallback.jpg"]


def test_extension_filter():
    assert idl.find_images(PAGE, "https://x.test/", {"png", "webp"}) == [
        "https://x.test/b.png", "https://x.test/lazy.webp"]


def test_file_name_and_free_path(tmp_path):
    assert idl.file_name("https://x.test/a/My%20Photo.JPG?size=2") == "My Photo.JPG"
    assert idl.file_name("https://x.test/img/pic", "image/png") == "pic.png"
    assert idl.file_name("https://x.test/") == "image.img"
    (tmp_path / "a.jpg").write_bytes(b"1")
    (tmp_path / "a-2.jpg").write_bytes(b"2")
    assert idl.free_path(tmp_path, "a.jpg").name == "a-3.jpg"
    assert idl.free_path(tmp_path, "new.jpg").name == "new.jpg"


def test_dry_run_downloads_nothing(tmp_path, capsys):
    page = tmp_path / "p.html"
    page.write_text(PAGE)
    out = tmp_path / "pics"
    assert idl.main([str(page), "--base", "https://x.test/", "--out", str(out)]) == 0
    text = capsys.readouterr().out
    assert "would download https://x.test/a.jpg" in text and "Dry run" in text
    assert not out.exists()


def test_apply_downloads_and_never_overwrites(base, tmp_path, capsys):
    page = tmp_path / "p.html"
    page.write_text('<img src="/img/one.png"><img src="/img/two">')
    out = tmp_path / "pics"
    args = [str(page), "--base", base, "--out", str(out), "--apply"]
    assert idl.main(args) == 0
    assert (out / "one.png").read_bytes() == b"\x89PNG-one"
    assert [p.read_bytes() for p in out.glob("two.*")] == [b"jpg"]
    assert idl.main(args) == 0  # second run keeps the first files and adds numbered copies
    assert (out / "one-2.png").exists() and (out / "one.png").read_bytes() == b"\x89PNG-one"
    assert "Downloaded 2 of 2" in capsys.readouterr().out


def test_failures_are_reported(base, tmp_path, capsys):
    page = tmp_path / "p.html"
    page.write_text('<img src="/missing.png"><img src="/page.txt">')
    assert idl.main([str(page), "--base", base, "--out", str(tmp_path / "o"), "--apply"]) == 1
    out = capsys.readouterr().out
    assert "failed" in out and "not an image" in out and "Downloaded 0 of 2" in out


def test_no_images(tmp_path, capsys):
    page = tmp_path / "p.html"
    page.write_text("<p>none</p>")
    assert idl.main([str(page)]) == 1
