import chart_generator as cg
import pytest

CSV = "month,revenue,costs\nJan,100,60\nFeb,\"1,200\",700\nMar,n/a,5\nApr,-50,10\n"


@pytest.fixture
def data(tmp_path):
    path = tmp_path / "d.csv"
    path.write_text(CSV, encoding="utf-8")
    return path


def test_read_series_skips_bad_rows_and_parses_thousands(data):
    labels, series, skipped = cg.read_series(data, "month", ["revenue", "costs"])
    assert labels == ["Jan", "Feb", "Apr"] and skipped == 1
    assert series == {"revenue": [100.0, 1200.0, -50.0], "costs": [60.0, 700.0, 10.0]}
    labels, _, _ = cg.read_series(data, None, ["costs"])
    assert labels == ["1", "2", "3", "4"]


def test_read_series_errors(data, tmp_path):
    with pytest.raises(KeyError):
        cg.read_series(data, "month", ["nope"])
    empty = tmp_path / "e.csv"
    empty.write_text("a,b\nx,y\n")
    with pytest.raises(ValueError):
        cg.read_series(empty, None, ["b"])


@pytest.mark.parametrize("low,high,expected", [
    (0, 97, (0, 100, 25)), (3, 8, (0, 8, 2)), (-50, 1200, (-500, 1500, 500)),
    (0, 0, (0, 1, 0.25))])
def test_nice_axis_includes_zero_and_covers_data(low, high, expected):
    lo, hi, step = cg.nice_axis(low, high)
    assert (lo, hi, step) == expected
    assert lo <= low and hi >= high


def test_number():
    assert [cg.number(v) for v in (5, 2.5, 1234.5, -3.14159)] == ["5", "2.5", "1,234", "-3.14"]


def test_svg_line_and_bar():
    labels, series = ["a", "b", "c"], {"one": [1.0, 4.0, 2.0], "two": [2.0, 1.0, 3.0]}
    line = cg.svg_chart(labels, series, "line", "My <chart>", 800, 400)
    assert line.startswith("<svg") and line.count("<polyline") == 2 and "My &lt;chart&gt;" in line
    assert "a (one): 1" in line and line.count("<circle") == 6
    bars = cg.svg_chart(labels, {"one": [1.0, -4.0, 2.0]}, "bar", None, 800, 400)
    assert bars.count("<rect") == 1 + 3 and "<polyline" not in bars  # background + 3 bars
    assert "aria-label=\"Chart\"" in bars


def test_text_chart_scales_bars():
    text = cg.text_chart(["a", "bb"], {"s": [10.0, -5.0]}, bar_width=10)
    assert text.splitlines()[0] == "s"
    assert "a  | " + "#" * 10 + " 10" in text and "bb | -" + "#" * 5 + " -5" in text


def test_cli_svg_text_and_protection(data, tmp_path, capsys):
    out = tmp_path / "c.svg"
    assert cg.main([str(data), "--x", "month", "--y", "revenue", "--y", "costs",
                    "--type", "bar", "--title", "T", "--output", str(out)]) == 0
    said = capsys.readouterr().out
    assert "3 point(s), 2 series" in said and "1 row(s) skipped" in said
    assert out.read_text().startswith("<svg")
    assert cg.main([str(data), "--y", "costs", "--output", str(out)]) == 1
    assert cg.main([str(data), "--y", "costs", "--output", str(out), "--force"]) == 0
    capsys.readouterr()
    assert cg.main([str(data), "--x", "month", "--y", "revenue", "--format", "text"]) == 0
    assert "Feb | " in capsys.readouterr().out


def test_cli_errors(data, capsys, tmp_path):
    assert cg.main([str(data), "--y", "missing"]) == 1
    assert "no column 'missing'" in capsys.readouterr().err
    assert cg.main([str(tmp_path / "none.csv"), "--y", "a"]) == 1
    with pytest.raises(SystemExit):
        cg.main([str(data), "--y", "costs", "--width", "10"])
