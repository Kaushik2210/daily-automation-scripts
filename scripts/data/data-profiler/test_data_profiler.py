import data_profiler as dp
import pytest


@pytest.mark.parametrize("values,kind", [
    (["1", "2", "-3"], "int"), (["1", "2.5"], "float"), (["yes", "No"], "bool"),
    (["2024-01-05", "2023-12-31"], "date"), (["a", "1"], "text"), ([], "empty")])
def test_guess_type(values, kind):
    assert dp.guess_type(values) == kind


def test_null_tokens():
    assert all(dp.is_null(t) for t in ["", " ", "NA", "n/a", "NULL", "None", "NaN", "-", "?"])
    assert not dp.is_null("0") and not dp.is_null("no")


def test_numeric_profile_statistics():
    info, warnings = dp.profile_column("x", ["1", "2", "3", "4", "", "n/a"], 3, 4)
    assert info["type"] == "int" and info["missing"] == 2 and info["unique"] == 4
    assert (info["min"], info["max"], info["mean"], info["median"]) == (1, 4, 2.5, 2.5)
    assert round(info["std"], 3) == 1.291
    assert sum(c for _, _, c in info["bins"]) == 4
    assert any("33% of values are missing" in w for w in warnings)


def test_histogram_edge_cases():
    assert dp.histogram([5, 5, 5], 4) == [(5, 5, 3)]
    bins = dp.histogram([0, 10], 2)
    assert [c for _, _, c in bins] == [1, 1] and bins[-1][1] == 10


def test_text_profile_and_warnings():
    info, warnings = dp.profile_column("t", ["a", "bb", "a", "a"], 2, 4)
    assert info["type"] == "text" and (info["min_len"], info["max_len"]) == (1, 2)
    assert info["top"][0] == ("a", 3) and warnings == []
    _, constant = dp.profile_column("c", ["x", "x", "x"], 2, 4)
    assert "every value is the same" in constant
    _, ids = dp.profile_column("id", ["a", "b", "c"], 2, 4)
    assert any("identifier" in w for w in ids)
    _, mixed = dp.profile_column("m", ["1", "2", "3", "4", "oops"], 2, 4)
    assert any("mostly numbers" in w and "oops" in w for w in mixed)


def test_fmt():
    assert dp.fmt(1500.0) == "1,500" and dp.fmt(3.0) == "3" and dp.fmt(2.5) == "2.50"


def test_cli_report(tmp_path, capsys):
    data = tmp_path / "d.csv"
    data.write_text("id,age,city,joined\n1,30,Pune,2024-01-01\n2,40,Pune,2024-02-01\n"
                    "3,,Delhi,2024-03-01\n3,,Delhi,2024-03-01\n")
    assert dp.main([str(data)]) == 0
    out = capsys.readouterr().out
    assert "d.csv: 4 rows x 4 columns, 1 duplicate row(s)" in out
    assert "age  [int]  2 values, 2 missing, 2 unique" in out and "50% of values are missing" in out
    assert "city  [text]" in out and "Pune (2)" in out and "joined  [date]" in out
    assert dp.main([str(data), "--columns", "city"]) == 0
    assert "age  [int]" not in capsys.readouterr().out


def test_cli_errors(tmp_path, capsys):
    data = tmp_path / "d.csv"
    data.write_text("a,b\n")
    assert dp.main([str(data)]) == 1
    assert "No data rows" in capsys.readouterr().err
    data.write_text("a,b\n1,2\n")
    with pytest.raises(SystemExit):
        dp.main([str(data), "--columns", "zzz"])
    with pytest.raises(SystemExit):
        dp.main([str(data), "--top", "0"])
    with pytest.raises(SystemExit):
        dp.main([str(tmp_path / "none.csv")])
