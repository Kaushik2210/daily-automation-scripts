import pytest
from json_to_csv import find_records, flatten, main, to_csv


def test_flatten_nested_and_lists():
    assert flatten({"a": {"b": 1, "c": {"d": 2}}, "t": [1, "x"], "n": None}) == {
        "a.b": 1, "a.c.d": 2, "t": '[1, "x"]', "n": None}


def test_find_records_variants():
    assert find_records([{"a": 1}]) == [{"a": 1}]
    assert find_records({"a": 1}) == [{"a": 1}]
    assert find_records({"data": {"rows": [{"a": 1}]}}, "data.rows") == [{"a": 1}]
    assert find_records({"meta": 1, "items": [{"a": 1}, {"a": 2}]}) == [{"a": 1}, {"a": 2}]
    two = {"x": [{"a": 1}], "y": [{"b": 2}]}
    assert find_records(two) == [two]
    with pytest.raises(ValueError):
        find_records([1, 2])


def test_to_csv_unions_columns_and_blanks_none():
    text, columns = to_csv([{"a": 1, "b": None}, {"a": 2, "c": {"d": 3}}])
    assert columns == ["a", "b", "c.d"]
    assert text.splitlines() == ["a,b,c.d", "1,,", "2,,3"]


def test_cli_errors_and_apply(tmp_path, capsys):
    src, out = tmp_path / "d.json", tmp_path / "d.csv"
    src.write_text('{"items": [{"x": 1}, {"x": 2}]}')
    assert main([str(src)]) == 0
    assert capsys.readouterr().out.splitlines() == ["x", "1", "2"]
    assert main([str(src), "--key", "items", "-o", str(out), "--apply"]) == 0
    assert out.read_text() == "x\n1\n2\n"
    src.write_text("[1, 2]")
    assert main([str(src)]) == 1
