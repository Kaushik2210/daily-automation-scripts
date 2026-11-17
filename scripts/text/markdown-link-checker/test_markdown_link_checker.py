import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import markdown_link_checker as mlc


def test_slugify_matches_github():
    assert mlc.slugify("Getting Started") == "getting-started"
    assert mlc.slugify("What's new? (v2)") == "whats-new-v2"
    assert mlc.slugify("`code` and **bold**") == "code-and-bold"


def test_scan_finds_links_headings_and_skips_code():
    text = ("# Title\n\n## Usage\n## Usage\n\nSee [a](a.md), ![img](pic.png \"t\"), `[x](n.md)`.\n"
            "```\n[skip](nope.md)\n```\n[ref link][docs] and [broken][gone]\n\n"
            "[docs]: https://example.com/docs\n")
    anchors, links = mlc.scan(text)
    assert anchors == {"title", "usage", "usage-1"}
    targets = {t for _, t in links}
    assert targets == {"a.md", "pic.png", "https://example.com/docs", "[gone]"}


def test_local_files_and_anchors(tmp_path):
    (tmp_path / "guide.md").write_text("# Guide\n\n## Setup steps\n")
    (tmp_path / "pic.png").write_bytes(b"x")
    page = tmp_path / "index.md"
    page.write_text("# Home\n[ok](guide.md) [anchor](guide.md#setup-steps) [self](#home)\n"
                    "![img](pic.png)\n[bad file](missing.md) [bad anchor](guide.md#nope)\n"
                    "[bad self](#nowhere) [mail](mailto:a@b.c) [web](https://example.com)\n")
    problems = mlc.check_file(page, tmp_path, False, 1, {}, {})
    no_anchor = "no heading with that anchor"
    assert sorted((t, why) for _, t, why in problems) == [
        ("#nowhere", no_anchor), ("guide.md#nope", no_anchor), ("missing.md", "file not found")]


def test_root_relative_links(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("[home](/README.md) [gone](/nope.md)\n")
    (tmp_path / "README.md").write_text("# Hi\n")
    problems = mlc.check_file(tmp_path / "docs" / "a.md", tmp_path, False, 1, {}, {})
    assert [t for _, t, _ in problems] == ["/nope.md"]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_HEAD(self):
        self.send_response(200 if self.path == "/ok" else 404)
        self.end_headers()


def test_external_links_with_a_local_server(tmp_path, capsys):
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        page = tmp_path / "a.md"
        page.write_text(f"[good]({base}/ok) [bad]({base}/missing)\n")
        assert mlc.main([str(page)]) == 0
        assert "Web links were not checked" in capsys.readouterr().out
        assert mlc.main([str(page), "--external"]) == 1
        out = capsys.readouterr().out
        assert "/missing  (HTTP 404)" in out and "/ok" not in out
    finally:
        server.shutdown()


def test_folder_scan_and_no_files(tmp_path, capsys):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "x.md").write_text("[a](nope.md)\n")
    assert mlc.main([str(tmp_path)]) == 1
    assert "1 broken link(s)" in capsys.readouterr().out
    empty = tmp_path / "empty"
    empty.mkdir()
    assert mlc.main([str(empty)]) == 1
