import argparse
import csv

import headline_collector as hc
import pytest

PAGE = """<h1>The Daily Example</h1>
<h2><a href="/budget">Council approves new city budget</a></h2>
<a href="/bridge"><h3>Bridge reopens after repairs</h3></a>
<h3>Schools add <em>coding</em> to the curriculum <a href="/schools">more</a></h3>
<h3>council APPROVES new city budget</h3>
<h3>Menu</h3><h2>About us</h2><h4>Deep heading with many words</h4>"""


def test_find_headlines_filters_dedupes_and_links():
    found = hc.find_headlines(PAGE, "https://news.test/")
    assert found == [
        {"text": "Council approves new city budget", "url": "https://news.test/budget"},
        {"text": "Bridge reopens after repairs", "url": "https://news.test/bridge"},
        {"text": "Schools add coding to the curriculum more", "url": "https://news.test/schools"},
    ]


def test_levels_and_min_words():
    texts = [h["text"] for h in hc.find_headlines(PAGE, levels=(1, 4), min_words=4)]
    assert "The Daily Example" not in texts and "Deep heading with many words" in texts
    assert [h["text"] for h in hc.find_headlines(PAGE, levels=(2,), min_words=1)] == [
        "Council approves new city budget", "About us"]


def test_parse_levels():
    assert hc.parse_levels("2") == (2,) and hc.parse_levels("1-3") == (1, 2, 3)
    for bad in ("x", "0-2", "3-9", "5-2"):
        with pytest.raises(argparse.ArgumentTypeError):
            hc.parse_levels(bad)


def test_levels_option_accepts_text_like_the_web_form_sends(tmp_path, capsys):
    page = tmp_path / "n.html"
    page.write_text("<h1>The big site title</h1><h2>An ordinary story headline</h2>")
    assert hc.main([str(page), "--levels", "2-3"]) == 0
    assert "The big site title" not in capsys.readouterr().out
    assert hc.main([str(page), "--levels", "1-6"]) == 0
    assert "The big site title" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        hc.main([str(page), "--levels", "2,3"])


def test_csv_collects_only_new_headlines(tmp_path, capsys):
    page, log = tmp_path / "news.html", tmp_path / "heads.csv"
    page.write_text(PAGE)
    assert hc.main([str(page), "--out", str(log)]) == 0
    assert "Added 3 new headline(s)" in capsys.readouterr().out
    assert hc.main([str(page), "--out", str(log)]) == 0
    assert "Nothing new" in capsys.readouterr().out
    page.write_text(PAGE + "<h2>A brand new story arrives</h2>")
    assert hc.main([str(page), "--out", str(log)]) == 0
    rows = list(csv.reader(log.open(encoding="utf-8")))
    assert rows[0] == hc.HEADER and len(rows) == 5 and rows[-1][2] == "A brand new story arrives"


def test_missing_sources_and_empty_pages_fail(tmp_path, capsys):
    page = tmp_path / "empty.html"
    page.write_text("<p>no headings</p>")
    assert hc.main([str(page)]) == 1
    assert hc.main([str(tmp_path / "gone.html")]) == 1
    assert "couldn't load" in capsys.readouterr().out
