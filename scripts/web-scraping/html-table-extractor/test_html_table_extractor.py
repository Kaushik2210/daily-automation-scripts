import csv

import html_table_extractor as hte

HTML = """<h1>Report</h1>
<table id="sales"><caption>Sales by region</caption>
<tr><th>Region</th><th>Q1</th></tr>
<tr><td>North</td><td>1,200</td></tr>
<tr><td colspan="2">Total &amp; more</td></tr></table>
<table><thead><tr><th>Name</th></tr></thead><tbody><tr><td>Ben<br>Smith</td></tr></tbody></table>
<table></table>"""


def test_extract_tables_with_caption_colspan_and_entities():
    tables = hte.extract_tables(HTML)
    assert len(tables) == 2  # the empty table is dropped
    sales = tables[0]
    assert (sales["caption"], sales["id"], sales["width"]) == ("Sales by region", "sales", 2)
    assert sales["rows"] == [["Region", "Q1"], ["North", "1,200"], ["Total & more", ""]]
    assert tables[1]["rows"] == [["Name"], ["Ben Smith"]]


def test_unclosed_cells_and_rows_and_nested_tables():
    loose = "<table><tr><td>a<td>b<tr><td>c<td>d</table>"
    assert hte.extract_tables(loose)[0]["rows"] == [["a", "b"], ["c", "d"]]
    nested = "<table><tr><td>outer<table><tr><td>inner</td></tr></table></td></tr></table>"
    found = {t["rows"][0][0] for t in hte.extract_tables(nested)}
    assert found == {"outer", "inner"}


def test_ragged_rows_are_padded():
    table = hte.extract_tables("<table><tr><td>1<td>2<td>3<tr><td>x</table>")[0]
    assert table["rows"] == [["1", "2", "3"], ["x", "", ""]]


def test_source_stem():
    assert hte.source_stem("https://example.com/stats/2026.html") == "example-com-stats-2026-html"
    assert hte.source_stem("Quarterly Report.html") == "quarterly-report"


def test_dry_run_writes_nothing(tmp_path, capsys):
    page = tmp_path / "page.html"
    page.write_text(HTML)
    out = tmp_path / "out"
    assert hte.main([str(page), "--out-dir", str(out)]) == 0
    text = capsys.readouterr().out
    assert "Table 1 (Sales by region): 3 row(s) x 2 column(s)" in text
    assert "Dry run" in text and not out.exists()


def test_apply_writes_csv_and_never_overwrites(tmp_path, capsys):
    page = tmp_path / "page.html"
    page.write_text(HTML)
    out = tmp_path / "out"
    assert hte.main([str(page), "--out-dir", str(out), "--apply", "--table", "1"]) == 0
    written = out / "page-table-1.csv"
    assert list(csv.reader(written.open(encoding="utf-8")))[1] == ["North", "1,200"]
    assert not (out / "page-table-2.csv").exists()
    written.write_text("keep me")
    assert hte.main([str(page), "--out-dir", str(out), "--apply", "--table", "1"]) == 0
    assert "already exists" in capsys.readouterr().out and written.read_text() == "keep me"


def test_no_tables_is_reported(tmp_path, capsys):
    page = tmp_path / "empty.html"
    page.write_text("<p>nothing</p>")
    assert hte.main([str(page)]) == 1
    assert "No matching tables" in capsys.readouterr().out
