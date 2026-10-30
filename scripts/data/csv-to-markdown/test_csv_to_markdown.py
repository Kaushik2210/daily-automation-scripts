from csv_to_markdown import main, to_markdown


def test_basic_table():
    table = to_markdown([["name", "score"], ["ada", "10"]])
    assert table.splitlines() == ["| name | score |", "| --- | --- |", "| ada | 10 |"]


def test_pipes_and_short_rows_and_align():
    table = to_markdown([["a", "b"], ["x|y"]], align="right")
    assert r"x\|y" in table
    assert table.splitlines()[1] == "| ---: | ---: |"
    assert table.splitlines()[2].endswith("|  |")


def test_empty_input():
    assert to_markdown([]) == ""


def test_cli_with_delimiter_and_bom(tmp_path, capsys):
    f = tmp_path / "d.csv"
    f.write_text("﻿city;pop\nrome;3\n", encoding="utf-8")
    main([str(f), "--delimiter", ";"])
    assert capsys.readouterr().out.splitlines()[0] == "| city | pop |"
