from datetime import date

import pytest
import rss_digest as rd

RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>Blog</title>
<item><title>Newer</title><link>https://x.test/new</link>
<pubDate>Tue, 13 Jan 2026 09:00:00 +0000</pubDate>
<description>&lt;p&gt;Hello &lt;b&gt;bold&lt;/b&gt; world&lt;/p&gt;</description></item>
<item><title>Older</title><link>https://x.test/old</link>
<pubDate>Mon, 15 Dec 2025 10:00:00 +0000</pubDate><description>Plain</description></item>
</channel></rss>"""

ATOM = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>Atom Blog</title>
<entry><title>Entry</title><link href="https://y.test/e"/>
<updated>2026-01-10T08:00:00Z</updated><summary>An entry</summary></entry></feed>"""


def test_parse_rss_and_atom():
    title, items = rd.parse_feed(RSS)
    assert title == "Blog" and [i["title"] for i in items] == ["Newer", "Older"]
    assert items[0]["summary"] == "Hello bold world"
    assert items[0]["date"].year == 2026 and items[1]["link"] == "https://x.test/old"
    title, items = rd.parse_feed(ATOM)
    assert title == "Atom Blog" and items[0]["link"] == "https://y.test/e"
    assert items[0]["date"].isoformat().startswith("2026-01-10T08:00:00")


def test_unsafe_and_invalid_feeds_are_refused():
    with pytest.raises(ValueError):
        rd.parse_feed('<!DOCTYPE x [<!ENTITY a "b">]><rss version="2.0"><channel/></rss>')
    with pytest.raises(ValueError):
        rd.parse_feed("<html><body/></html>")


def test_parse_date_and_summary():
    assert rd.parse_date("nonsense") is None and rd.parse_date(None) is None
    assert rd.parse_date("2026-01-10").tzinfo is not None
    assert rd.clean_summary("a" * 300).endswith("...") and len(rd.clean_summary("a" * 300)) == 160


def test_digest_since_limit_and_order():
    feeds = [rd.parse_feed(RSS), rd.parse_feed(ATOM)]
    text = rd.build_digest(feeds, since=date(2026, 1, 1))
    assert text.startswith("# Feed digest (2 item(s) from 2 feed(s))")
    assert "Older" not in text and text.index("Newer") < text.index("Entry")
    assert "- **Newer** (2026-01-13) - Hello bold world [read](https://x.test/new)" in text
    both = rd.build_digest([rd.parse_feed(RSS)], limit=1)
    assert "Newer" in both and "Older" not in both


def test_cli_preview_apply_and_bad_feed(tmp_path, capsys):
    feed, out = tmp_path / "feed.xml", tmp_path / "digest.md"
    feed.write_text(RSS, encoding="utf-8")
    bad = tmp_path / "bad.xml"
    bad.write_text("not xml")
    assert rd.main([str(feed), "-o", str(out)]) == 0 and not out.exists()
    assert "Newer" in capsys.readouterr().out
    assert rd.main([str(feed), "-o", str(out), "--apply"]) == 0 and out.exists()
    assert rd.main([str(feed), "-o", str(out), "--apply"]) == 1
    assert rd.main([str(feed), str(bad)]) == 1
    assert "Skipped" in capsys.readouterr().err
