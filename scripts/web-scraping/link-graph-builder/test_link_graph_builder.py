import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import link_graph_builder as lgb
import pytest

SITE = {
    "index.html": '<title>Home</title><a href="about.html">a</a><a href="blog/">b</a>'
                  '<a href="https://github.com/x">gh</a><a href="mailto:a@b.c">m</a>',
    "about.html": '<title>About</title><a href="index.html#top">home</a>'
                  '<a href="missing.html">x</a><a href="/blog/post.html">p</a>'
                  '<a href="logo.png">img</a>',
    "blog/index.html": '<title>Blog</title><a href="post.html">p</a><a href="../index.html">h</a>',
    "blog/post.html": "<title>Post</title><p>The end.</p>",
    "orphan.html": '<title>Orphan</title><a href="index.html">home</a>',
    "logo.png": "binary",
}


@pytest.fixture
def site(tmp_path):
    for name, text in SITE.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return tmp_path


def test_parse_page():
    title, hrefs = lgb.parse_page("<title> My \n Page </title><a href=' /x '>1</a><a>2</a>"
                                  "<a href=''>3</a>")
    assert title == "My Page" and hrefs == ["/x"]


@pytest.mark.parametrize("page,href,expected", [
    ("index.html", "about.html", ("page", "about.html")),
    ("index.html", "blog/", ("page", "blog/index.html")),
    ("blog/index.html", "../about.html#x", ("page", "about.html")),
    ("about.html", "/blog/post.html", ("page", "blog/post.html")),
    ("index.html", "blog", ("page", "blog/index.html")),
    ("index.html", "logo.png", ("asset", None)),
    ("index.html", "nope.html", ("broken", None)),
    ("index.html", "../../x.html", ("broken", None)),
    ("index.html", "https://Example.org/a", ("external", "example.org")),
    ("index.html", "//cdn.example.org/lib.js", ("external", "cdn.example.org")),
    ("index.html", "mailto:a@b.c", ("ignore", None)), ("index.html", "#top", ("ignore", None)),
    ("index.html", "?page=2", ("ignore", None))])
def test_local_resolver(page, href, expected):
    pages = {"index.html", "about.html", "blog/index.html", "blog/post.html"}
    assert lgb.local_resolver(pages, {"logo.png"})(page, href) == expected


def test_build_graph_from_a_folder(site):
    pages, assets = lgb.local_site(site)
    resolve = lgb.local_resolver(set(pages), assets)
    nodes = lgb.build_graph("index.html", lambda k: pages[k].read_text(), resolve)
    assert set(nodes) == {"index.html", "about.html", "blog/index.html", "blog/post.html"}
    assert nodes["index.html"]["out"] == ["about.html", "blog/index.html"]
    assert nodes["index.html"]["external"] == ["github.com"]
    assert nodes["about.html"]["broken"] == ["missing.html"]
    assert nodes["blog/index.html"]["out"] == ["blog/post.html", "index.html"]
    facts = lgb.analyse(nodes, "index.html")
    assert facts["inbound"]["blog/post.html"] == 2 and facts["dead_ends"] == ["blog/post.html"]
    assert facts["broken"] == [("about.html", "missing.html")]
    assert lgb.levels(nodes, "index.html") == {"index.html": 0, "about.html": 1,
                                               "blog/index.html": 1, "blog/post.html": 2}


def test_max_pages_limits_the_walk(site):
    pages, assets = lgb.local_site(site)
    nodes = lgb.build_graph("index.html", lambda k: pages[k].read_text(),
                            lgb.local_resolver(set(pages), assets), max_pages=2)
    assert len(nodes) == 2


def test_to_dot_marks_missing_pages():
    nodes = {"a": {"title": 'He said "hi"', "out": ["b"], "external": [], "broken": [],
                   "missing": False},
             "b": {"title": "", "out": [], "external": [], "broken": [], "missing": True}}
    dot = lgb.to_dot(nodes)
    assert "digraph site {" in dot and '"a" -> "b";' in dot and "He said 'hi'" in dot
    assert '"b" [label="b", color=red];' in dot


def test_cli_folder_report_and_exports(site, tmp_path, capsys):
    dot, js = tmp_path / "g.dot", tmp_path / "g.json"
    assert lgb.main(["--dir", str(site), "--dot", str(dot), "--json", str(js)]) == 1
    out = capsys.readouterr().out
    assert "4 page(s), 6 internal link(s), 1 external site(s); start: index.html" in out
    assert "Not reachable by clicking from the start page (orphans):\n  orphan.html" in out
    assert "Dead ends (no links out): blog/post.html" in out
    assert "about.html  ->  missing.html" in out and "External sites linked: github.com" in out
    assert "  2: blog/post.html" in out
    assert "digraph site" in dot.read_text() and json.loads(js.read_text())["start"] == "index.html"
    assert lgb.main(["--dir", str(site), "--dot", str(dot)]) == 1
    assert "already exists" in capsys.readouterr().err


def test_clean_site_exits_zero(tmp_path, capsys):
    (tmp_path / "index.html").write_text('<a href="b.html">b</a>')
    (tmp_path / "b.html").write_text('<a href="index.html">home</a>')
    assert lgb.main(["--dir", str(tmp_path)]) == 0
    with pytest.raises(SystemExit):
        lgb.main(["--dir", str(tmp_path / "none")])
    with pytest.raises(SystemExit):
        lgb.main(["--dir", str(tmp_path), "--start", "zzz.html"])
    empty = tmp_path / "empty"
    empty.mkdir()
    assert lgb.main(["--dir", str(empty)]) == 1


PAGES = {"/": '<title>Home</title><a href="/a">a</a><a href="https://other.test/">o</a>',
         "/a": '<title>A</title><a href="/b">b</a><a href="/">home</a>',
         "/b": "<title>B</title><p>no links</p>"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        body = PAGES.get(self.path)
        self.send_response(200 if body else 404)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write((body or "").encode())


def test_live_crawl_needs_fetch_and_stays_on_the_site(capsys):
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/"
    try:
        assert lgb.main(["--url", base]) == 0
        assert "Add --fetch" in capsys.readouterr().out
        assert lgb.main(["--url", base, "--fetch", "--delay", "0"]) == 0
        out = capsys.readouterr().out
        assert "3 page(s), 3 internal link(s), 1 external site(s)" in out
        assert "other.test" in out and "Dead ends (no links out)" in out
    finally:
        server.shutdown()
