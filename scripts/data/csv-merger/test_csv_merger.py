from csv_merger import main, merge, read_dicts


def test_merge_union_of_columns_in_first_seen_order():
    tables = [(["id", "name"], [{"id": "1", "name": "a"}]),
              (["id", "email"], [{"id": "2", "email": "b@x"}])]
    columns, rows = merge(tables)
    assert columns == ["id", "name", "email"]
    assert rows == [{"id": "1", "name": "a", "email": ""}, {"id": "2", "name": "", "email": "b@x"}]


def test_merge_with_source_column():
    columns, rows = merge([(["a"], [{"a": "1"}]), (["a"], [{"a": "2"}])], ["x.csv", "y.csv"])
    assert columns == ["a", "source"]
    assert [r["source"] for r in rows] == ["x.csv", "y.csv"]


def test_read_dicts_handles_empty_file(tmp_path):
    f = tmp_path / "e.csv"
    f.write_text("")
    assert read_dicts(f) == ([], [])


def test_cli_dry_run_then_apply(tmp_path, capsys):
    a, b, out = tmp_path / "a.csv", tmp_path / "b.csv", tmp_path / "all.csv"
    a.write_text("id,name\n1,Ada\n")
    b.write_text("id,name\n2,Lin\n")
    main([str(a), str(b), "-o", str(out)])
    assert not out.exists()
    assert "Merged: 2 row(s)" in capsys.readouterr().out
    main([str(a), str(b), "-o", str(out), "--apply", "--add-source"])
    assert out.read_text().splitlines() == ["id,name,source", "1,Ada,a.csv", "2,Lin,b.csv"]
