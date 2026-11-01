from csv_cleaner import clean_header, clean_rows, main, unique

MESSY = "  First Name ,Last Name!, Age \n Ada , Lovelace , 36\n\n  ,  ,  \nLin,Chen\n"


def test_clean_header_and_unique():
    assert clean_header("  First Name! ") == "first_name"
    assert clean_header("###") == "column"
    assert unique(["a", "a", "b", "a"]) == ["a", "a_2", "b", "a_3"]


def test_clean_rows_stats():
    rows = [["  First Name ", "Age"], [" Ada ", "36"], ["", " "], ["Lin"]]
    cleaned, stats = clean_rows(rows)
    assert cleaned == [["first_name", "age"], ["Ada", "36"], ["Lin", ""]]
    assert stats == {"blank_rows": 1, "trimmed_cells": 3, "padded_rows": 1}


def test_keep_headers():
    cleaned, _ = clean_rows([["Keep Me"], ["x"]], normalize_headers=False)
    assert cleaned[0] == ["Keep Me"]


def test_dry_run_then_apply(tmp_path, capsys):
    src, out = tmp_path / "in.csv", tmp_path / "out.csv"
    src.write_text(MESSY)
    main([str(src), "-o", str(out)])
    assert not out.exists()
    assert "Dry run" in capsys.readouterr().out
    main([str(src), "-o", str(out), "--apply"])
    lines = out.read_text().splitlines()
    assert lines[0] == "first_name,last_name,age"
    assert lines[1] == "Ada,Lovelace,36"
    assert src.read_text() == MESSY
