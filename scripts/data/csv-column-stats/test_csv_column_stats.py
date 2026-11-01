from csv_column_stats import column_stats, describe_column, fmt, main, to_number


def test_to_number():
    assert to_number("1,234.5") == 1234.5
    assert to_number("abc") is None


def test_numeric_column():
    info = describe_column(["1", "2", "3", "", "10"])
    assert info["kind"] == "number"
    assert (info["min"], info["max"], info["median"]) == (1, 10, 2.5)
    assert info["mean"] == 4 and info["blank"] == 1 and info["count"] == 4


def test_text_column_top_values():
    info = describe_column(["a", "b", "a", "a", "c", "b"])
    assert info["kind"] == "text"
    assert info["top"][0] == ("a", 3) and info["unique"] == 3


def test_mixed_column_is_text_and_short_rows_ok():
    stats = column_stats([["x", "y"], ["1", "z"], ["oops"], ["3", "z"]])
    assert stats["x"]["kind"] == "text"
    assert stats["y"]["blank"] == 1 and fmt(2.50) == "2.5" and fmt(3.0) == "3"


def test_cli(tmp_path, capsys):
    f = tmp_path / "d.csv"
    f.write_text("name,score\nada,10\nlin,7\nada,\n")
    main([str(f)])
    out = capsys.readouterr().out
    assert "3 data row(s), 2 column(s)" in out
    assert "score  [number]" in out and "ada (2)" in out
