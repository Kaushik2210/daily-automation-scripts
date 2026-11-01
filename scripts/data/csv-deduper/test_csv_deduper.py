from csv_deduper import dedupe, main

ROWS = [["id", "email"], ["1", "a@x"], ["2", "A@x"], ["3", "b@x"], ["4", "a@x"]]


def test_all_columns_only_exact_duplicates():
    kept, removed = dedupe([["a"], ["x"], ["x"], ["y"]])
    assert kept == [["a"], ["x"], ["y"]] and removed == 1


def test_selected_column_keep_first_and_last():
    first, n = dedupe(ROWS, ["email"])
    assert [r[0] for r in first[1:]] == ["1", "2", "3"] and n == 1
    last, _ = dedupe(ROWS, ["email"], keep="last")
    assert [r[0] for r in last[1:]] == ["2", "3", "4"]


def test_ignore_case():
    kept, removed = dedupe(ROWS, ["email"], ignore_case=True)
    assert [r[0] for r in kept[1:]] == ["1", "3"] and removed == 2


def test_cli_unknown_column_and_apply(tmp_path, capsys):
    src, out = tmp_path / "d.csv", tmp_path / "clean.csv"
    src.write_text("id,email\n1,a@x\n2,a@x\n")
    try:
        main([str(src), "--columns", "nope"])
    except SystemExit as err:
        assert err.code == 2
    main([str(src), "--columns", "email", "-o", str(out)])
    assert not out.exists()
    main([str(src), "--columns", "email", "-o", str(out), "--apply"])
    assert out.read_text().splitlines() == ["id,email", "1,a@x"]
