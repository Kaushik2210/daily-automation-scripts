import json

import html_dashboard_builder as hdb
import pytest

DATA = {
    "title": "Sales <b>board</b>", "subtitle": "Q4",
    "metrics": [{"label": "Revenue", "value": 48210.5, "unit": "$", "change": 3.1},
                {"label": "Churn", "value": 2.4, "unit": "%", "change": -0.3,
                 "lower_is_better": True},
                {"label": "Bugs", "value": 9, "change": 12, "lower_is_better": True},
                {"label": "Flat", "value": 1, "change": 0}],
    "charts": [{"title": "Line", "type": "line", "labels": ["a", "b"], "values": [1, 5]},
               {"title": "Bars", "type": "bar", "labels": ["x", "y", "z"], "values": [0, 3, 9]}],
    "tables": [{"title": "T", "columns": ["Page", "Views"], "rows": [["/a<b>", 1200], ["/b", 5]]}]}


def test_fmt():
    assert [hdb.fmt(v) for v in (1200, 1200.0, 2.5, 3.14159, "x", True)] == [
        "1,200", "1,200", "2.5", "3.14", "x", "True"]


def test_metric_cards_colour_the_change_by_direction():
    cards = [hdb.metric_card(m) for m in DATA["metrics"]]
    assert "$48,210.5" in cards[0] and "change good" in cards[0]
    assert "2.4%" in cards[1] and "change good" in cards[1]  # lower churn is better
    assert "change bad" in cards[2] and "change flat" in cards[3]


def test_nice_max():
    assert [hdb.nice_max(v) for v in (0, 0.4, 7, 9, 42, 1234)] == [1, 0.4, 7, 9, 50, 2000]


def test_charts_are_accessible_svg():
    line = hdb.chart_svg(DATA["charts"][0])
    assert line.startswith("<svg") and "<polyline" in line and 'aria-label="Line"' in line
    assert "<title>b: 5</title>" in line
    bars = hdb.chart_svg(DATA["charts"][1])
    assert bars.count('class="bar"') == 3 and "<polyline" not in bars
    with pytest.raises(ValueError):
        hdb.chart_svg({"labels": ["a"], "values": [1, 2]})


def test_html_is_escaped_and_self_contained():
    page = hdb.build(DATA)
    assert "Sales &lt;b&gt;board&lt;/b&gt;" in page and "<b>board</b>" not in page
    assert "/a&lt;b&gt;" in page and 'class="num">1,200' in page
    assert "http://" not in page.replace("http://www.w3.org", "") and "<script" not in page
    assert "prefers-color-scheme:dark" in page and 'lang="en"' in page


def test_cli(tmp_path, capsys):
    src = tmp_path / "d.json"
    src.write_text(json.dumps(DATA))
    out = tmp_path / "dash.html"
    assert hdb.main([str(src), "--output", str(out)]) == 0
    assert out.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert "no internet" in capsys.readouterr().out
    assert hdb.main([str(src), "--output", str(out)]) == 1
    assert hdb.main([str(src), "--output", str(out), "--force"]) == 0
    assert hdb.main([str(src)]) == 0 and "<main>" in capsys.readouterr().out


def test_bad_input(tmp_path, capsys):
    broken = tmp_path / "b.json"
    broken.write_text(json.dumps({"metrics": [{"value": 1}]}))
    assert hdb.main([str(broken)]) == 1
    assert "Can't build the dashboard" in capsys.readouterr().err
    assert hdb.main([str(tmp_path / "missing.json")]) == 1
    minimal = tmp_path / "m.json"
    minimal.write_text("{}")
    assert hdb.main([str(minimal)]) == 0
