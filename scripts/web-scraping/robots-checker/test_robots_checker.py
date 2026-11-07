import pytest
import robots_checker as rc

ROBOTS = """# test
User-agent: *
Disallow: /admin/
Disallow: /private
Allow: /private/public/
Disallow: /*.pdf$
Crawl-delay: 5

User-agent: BadBot
Disallow: /

User-agent: Googlebot
User-agent: Bingbot
Disallow: /nogoogle

Sitemap: https://example.com/sitemap.xml
"""


def allowed(agent, path):
    groups, _ = rc.parse_robots(ROBOTS)
    return rc.is_allowed(rc.pick_group(groups, agent), path)[0]


def test_parse_groups_and_sitemaps():
    groups, sitemaps = rc.parse_robots(ROBOTS)
    assert [g["agents"] for g in groups] == [["*"], ["badbot"], ["googlebot", "bingbot"]]
    assert groups[0]["delay"] == 5.0 and sitemaps == ["https://example.com/sitemap.xml"]


def test_longest_match_wins_over_file_order():
    assert allowed("*", "/private/secret") is False
    assert allowed("*", "/private/public/page") is True      # Allow is longer than Disallow
    assert allowed("*", "/admin/users") is False
    assert allowed("*", "/products") is True


def test_wildcards_and_end_anchor():
    assert allowed("*", "/files/report.pdf") is False
    assert allowed("*", "/files/report.pdf?download=1") is True   # $ anchors the end
    assert allowed("*", "/files/report.pdfx") is True


def test_agent_selection_and_default():
    assert allowed("BadBot/2.1", "/anything") is False
    assert allowed("Googlebot", "/nogoogle") is False
    assert allowed("Googlebot", "/admin/") is True           # its own group has no /admin rule
    assert allowed("SomeOtherBot", "/admin/") is False       # falls back to *


def test_no_robots_means_allowed_and_empty_disallow():
    assert rc.is_allowed(None, "/x") == (True, None)
    groups, _ = rc.parse_robots("User-agent: *\nDisallow:\n")
    assert rc.is_allowed(groups[0], "/anything") == (True, None)


def test_path_of():
    assert rc.path_of("https://x.test/a/b?q=1#frag") == "/a/b?q=1"
    assert rc.path_of("https://x.test") == "/"


def test_cli_with_saved_file(tmp_path, capsys):
    f = tmp_path / "robots.txt"
    f.write_text(ROBOTS)
    code = rc.main(["--robots", str(f), "/private/public/x", "/admin/panel"])
    out = capsys.readouterr().out
    assert code == 1 and "ALLOWED /private/public/x" in out and "BLOCKED /admin/panel" in out
    assert "Crawl-delay for *: 5 seconds" in out
    assert "Sitemaps: https://example.com/sitemap.xml" in out
    assert rc.main(["--robots", str(f), "/ok"]) == 0
    with pytest.raises(SystemExit):
        rc.main(["--robots", str(tmp_path / "nope.txt"), "/x"])
