import gzip
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import sitemap_crawler as sc

URLSET = """<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://example.com/</loc><lastmod>2026-01-10</lastmod></url>
<url><loc>https://example.com/admin/users</loc></url>
<url><loc>https://example.com/private/public/faq</loc></url>
<url><loc>https://other.example.org/page</loc></url>
</urlset>"""
INDEX = """<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>https://example.com/a.xml</loc></sitemap><sitemap><loc>https://example.com/b.xml</loc>
</sitemap></sitemapindex>"""
ROBOTS = """User-agent: *
Disallow: /admin/
Disallow: /private
Allow: /private/public/
Crawl-delay: 5

User-agent: BadBot
Disallow: /

Sitemap: https://example.com/sitemap.xml
"""


def test_parse_urlset_and_index():
    kind, items = sc.parse_sitemap(URLSET)
    assert kind == "urlset" and items[0] == ("https://example.com/", "2026-01-10")
    assert len(items) == 4 and items[1][1] == ""
    kind, sitemaps = sc.parse_sitemap(INDEX)
    assert kind == "index" and sitemaps == ["https://example.com/a.xml",
                                            "https://example.com/b.xml"]
    with pytest.raises(ValueError, match="not a sitemap"):
        sc.parse_sitemap("<html></html>")


def test_robots_rules_and_agents():
    rules = sc.load_robots(ROBOTS)
    assert rules.can_fetch("*", "https://example.com/products")
    assert not rules.can_fetch("*", "https://example.com/admin/users")
    assert not rules.can_fetch("*", "https://example.com/private/notes")
    assert rules.can_fetch("*", "https://example.com/private/public/faq")
    assert not rules.can_fetch("BadBot", "https://example.com/")
    assert rules.crawl_delay("*") == 5 and rules.site_maps() == ["https://example.com/sitemap.xml"]


def test_page_title():
    assert sc.page_title("<html><TITLE>\n  Hello   world </TITLE>") == "Hello world"
    assert sc.page_title("<p>no title</p>") == ""


def test_crawl_waits_between_requests_only():
    sleeps, lines = [], []
    results = sc.crawl(["a", "b", "c"], 2.5, lambda u: {"url": u, "line": f"got {u}"},
                       sleep=sleeps.append, out=lines.append)
    assert sleeps == [2.5, 2.5] and lines == ["got a", "got b", "got c"] and len(results) == 3


def test_offline_listing_with_local_files(tmp_path, capsys):
    sitemap, robots = tmp_path / "s.xml", tmp_path / "robots.txt"
    sitemap.write_text(URLSET)
    robots.write_text(ROBOTS)
    assert sc.main(["--sitemap", str(sitemap), "--robots", str(robots)]) == 0
    out = capsys.readouterr().out
    assert "4 URL(s) in the sitemap, robots rules for '*'" in out
    assert "allowed     https://example.com/  (modified 2026-01-10)" in out
    assert "BLOCKED     https://example.com/admin/users" in out
    assert "allowed     https://example.com/private/public/faq" in out
    assert "OTHER SITE  https://other.example.org/page" in out
    assert "2 allowed, 1 blocked by robots.txt, 1 on other sites (skipped)." in out
    assert "Crawl-delay of 5" in out and "Use --fetch" in out
    assert sc.main(["--sitemap", str(sitemap), "--robots", str(robots), "--agent", "BadBot"]) == 0
    assert "0 allowed, 3 blocked" in capsys.readouterr().out
    assert sc.main(["--sitemap", str(sitemap), "--limit", "1"]) == 0
    assert "1 URL(s) in the sitemap, no robots.txt checked" in capsys.readouterr().out


def test_index_listing_and_bad_files(tmp_path, capsys):
    index = tmp_path / "i.xml"
    index.write_text(INDEX)
    assert sc.main(["--sitemap", str(index)]) == 0
    assert "Sitemap index with 2 sitemap(s)" in capsys.readouterr().out
    broken = tmp_path / "b.xml"
    broken.write_text("<urlset")
    assert sc.main(["--sitemap", str(broken)]) == 1
    assert "Can't read the sitemap" in capsys.readouterr().err
    assert sc.main(["--sitemap", str(tmp_path / "none.xml")]) == 1


class Handler(BaseHTTPRequestHandler):
    base = ""
    hits = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        Handler.hits.append(self.path)
        if self.path == "/sitemap.xml":
            body = gzip.compress(URLSET.replace("https://example.com", Handler.base).replace(
                "https://other.example.org", "https://elsewhere.test").encode())
        elif self.path == "/robots.txt":
            body = ROBOTS.replace("Crawl-delay: 5\n", "").encode()
        elif self.path == "/gone":
            self.send_response(404)
            self.end_headers()
            return
        else:
            body = b"<html><title>Page " + self.path.encode() + b"</title></html>"
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)


def test_remote_sitemap_robots_discovery_and_polite_crawl(capsys):
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    Handler.base = f"http://127.0.0.1:{server.server_address[1]}"
    Handler.hits = []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        sitemap = f"{Handler.base}/sitemap.xml"
        assert sc.main(["--sitemap", sitemap, "--fetch", "--delay", "0"]) == 0
        out = capsys.readouterr().out
        assert "BLOCKED" in out and "Visiting 2 page(s)" in out
        assert "Page /private/public/faq" in out
        assert "/admin/users" not in "".join(h for h in Handler.hits)  # blocked pages never fetched
        assert "/robots.txt" in Handler.hits and "2 fetched, 0 failed." in out
    finally:
        server.shutdown()


def test_longest_rule_wins_and_wildcards():
    rules = sc.load_robots("User-agent: *\nDisallow: /shop/\nAllow: /shop/sale/\n"
                           "Disallow: /*.pdf$\nDisallow: /tmp\nAllow: /tmp\n")
    assert not rules.can_fetch("*", "https://x.org/shop/cart")
    assert rules.can_fetch("*", "https://x.org/shop/sale/1")
    assert not rules.can_fetch("*", "https://x.org/docs/a.pdf")
    assert rules.can_fetch("*", "https://x.org/docs/a.pdf.html")
    assert rules.can_fetch("*", "https://x.org/tmp")  # equal length: Allow wins
    assert rules.can_fetch("*", "https://x.org/")


def test_most_specific_agent_group_is_used():
    rules = sc.load_robots("User-agent: *\nDisallow: /a\n\nUser-agent: Googlebot\n"
                           "User-agent: Bingbot\nDisallow: /b\n")
    assert rules.can_fetch("SomeBot", "https://x.org/b") and not rules.can_fetch(
        "SomeBot", "https://x.org/a")
    assert rules.can_fetch("Googlebot/2.1", "https://x.org/a")
    assert not rules.can_fetch("Bingbot", "https://x.org/b")
    assert sc.load_robots("").can_fetch("*", "https://x.org/anything")
    assert sc.load_robots("User-agent: *\nDisallow:\n").can_fetch("*", "https://x.org/x")
