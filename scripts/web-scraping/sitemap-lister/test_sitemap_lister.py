from datetime import date

import pytest
import sitemap_lister as sl

URLSET = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://x.test/</loc><lastmod>2026-01-10</lastmod></url>
<url><loc>https://x.test/products/a</loc><lastmod>2025-12-20T08:00:00+00:00</lastmod></url>
<url><loc>https://x.test/blog</loc></url></urlset>"""

INDEX = """<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>https://x.test/s1.xml</loc><lastmod>2026-01-01</lastmod></sitemap>
<sitemap><loc>https://x.test/s2.xml</loc></sitemap></sitemapindex>"""


def test_parse_urlset_and_index():
    kind, entries = sl.parse_sitemap(URLSET)
    assert kind == "urlset" and entries[0] == ("https://x.test/", "2026-01-10")
    assert entries[2] == ("https://x.test/blog", "")
    kind, entries = sl.parse_sitemap(INDEX)
    assert kind == "sitemapindex" and [e[0] for e in entries] == [
        "https://x.test/s1.xml", "https://x.test/s2.xml"]


def test_unsafe_or_wrong_documents_are_refused():
    with pytest.raises(ValueError):
        sl.parse_sitemap('<!DOCTYPE x [<!ENTITY a "b">]><urlset/>')
    with pytest.raises(ValueError):
        sl.parse_sitemap("<html/>")


def test_lastmod_date_and_filters():
    assert sl.lastmod_date("2025-12-20T08:00:00+00:00") == date(2025, 12, 20)
    assert sl.lastmod_date("") is None
    _, entries = sl.parse_sitemap(URLSET)
    assert [e[0] for e in sl.filter_entries(entries, contains="PRODUCTS")] == [
        "https://x.test/products/a"]
    recent = sl.filter_entries(entries, newer_than=date(2026, 1, 1))
    assert [e[0] for e in recent] == ["https://x.test/"]          # undated entries are dropped


def test_cli_text_csv_limit_and_errors(tmp_path, capsys):
    f = tmp_path / "sitemap.xml"
    f.write_text(URLSET, encoding="utf-8")
    assert sl.main([str(f)]) == 0
    out = capsys.readouterr().out
    assert "2026-01-10  https://x.test/" in out and "3 of 3 URL(s)." in out
    assert sl.main([str(f), "--limit", "1", "--newer-than", "2025-12-01"]) == 0
    assert "1 of 3 URL(s)." in capsys.readouterr().out
    assert sl.main([str(f), "--csv"]) == 0
    assert capsys.readouterr().out.splitlines()[0] == "url,lastmod"
    idx = tmp_path / "index.xml"
    idx.write_text(INDEX)
    sl.main([str(idx)])
    assert "sitemap index" in capsys.readouterr().out
    bad = tmp_path / "bad.xml"
    bad.write_text("nope")
    assert sl.main([str(bad)]) == 1
    with pytest.raises(SystemExit):
        sl.main([str(f), "--newer-than", "soon"])
