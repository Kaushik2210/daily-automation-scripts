import json

from csv_to_json import convert_value, main, rows_to_records


def test_convert_value():
    assert convert_value("12") == 12
    assert convert_value("3.5") == 3.5
    assert convert_value("TRUE") is True
    assert convert_value("  ") is None
    assert convert_value("007x") == "007x"


def test_records_plain_and_typed():
    rows = [["name", "age", "ok"], ["Ada", "36", "true"], ["Lin"]]
    assert rows_to_records(rows)[0] == {"name": "Ada", "age": "36", "ok": "true"}
    typed = rows_to_records(rows, infer_types=True)
    assert typed[0] == {"name": "Ada", "age": 36, "ok": True}
    assert typed[1] == {"name": "Lin", "age": None, "ok": None}


def test_empty_input():
    assert rows_to_records([]) == []


def test_cli_lines_and_apply(tmp_path, capsys):
    src, out = tmp_path / "d.csv", tmp_path / "d.json"
    src.write_text("a,b\n1,x\n2,y\n")
    main([str(src), "--lines", "--types"])
    lines = capsys.readouterr().out.strip().splitlines()
    assert [json.loads(line) for line in lines] == [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
    main([str(src), "-o", str(out), "--apply"])
    assert len(json.loads(out.read_text())) == 2
