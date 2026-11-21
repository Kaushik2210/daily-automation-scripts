import sqlite3

import pytest
import sqlite_csv_importer as sci


@pytest.mark.parametrize("name,expected", [
    ("Order ID", "order_id"), ("  Price ($)  ", "price"), ("2024 sales", "_2024_sales"),
    ("", "column"), ("É-mail", "mail")])
def test_clean_name(name, expected):
    assert sci.clean_name(name) == expected


def test_clean_name_avoids_duplicates():
    names = []
    for original in ["Name", "name", "NAME!"]:
        names.append(sci.clean_name(original, names))
    assert names == ["name", "name_2", "name_3"]


@pytest.mark.parametrize("values,kind", [
    (["1", "2", ""], "INTEGER"), (["1.5", "2"], "REAL"), (["a", "1"], "TEXT"),
    (["007", "12"], "TEXT"), ([], "TEXT"), (["1e3", "2"], "REAL"), (["nan", "1"], "INTEGER"),
    (["inf"], "TEXT")])
def test_column_type(values, kind):
    assert sci.column_type(values) == kind


def test_convert():
    assert sci.convert(" 5 ", "INTEGER") == 5 and sci.convert("2.5", "REAL") == 2.5
    assert sci.convert("", "INTEGER") is None and sci.convert("N/A", "TEXT") is None
    assert sci.convert(" hi ", "TEXT") == "hi"


def write_csv(path, text):
    path.write_text(text)
    return path


def rows(db, table):
    with sqlite3.connect(db) as con:
        return con.execute(f"SELECT * FROM {table}").fetchall()


def test_dry_run_creates_nothing(tmp_path, capsys):
    data = write_csv(tmp_path / "People List.csv", "Full Name,Age\nAda,36\nBob,\n")
    db = tmp_path / "x.db"
    assert sci.main([str(data), "--db", str(db)]) == 0
    out = capsys.readouterr().out
    assert "People List.csv -> table people_list (create): 2 row(s)" in out
    assert "full_name" in out and "(from 'Full Name')" in out and "INTEGER" in out
    assert "Dry run" in out and not db.exists()


def test_apply_imports_typed_values(tmp_path, capsys):
    data = write_csv(tmp_path / "people.csv", "name,age,score\nAda,36,1.5\nBob,,2\n")
    db = tmp_path / "x.db"
    assert sci.main([str(data), "--db", str(db), "--apply"]) == 0
    assert rows(db, "people") == [("Ada", 36, 1.5), ("Bob", None, 2.0)]
    assert "now has 2 row(s)" in capsys.readouterr().out


def test_existing_table_policies(tmp_path, capsys):
    data = write_csv(tmp_path / "t.csv", "a,b\n1,x\n")
    db = tmp_path / "x.db"
    sci.main([str(data), "--db", str(db), "--apply"])
    assert sci.main([str(data), "--db", str(db), "--apply"]) == 1
    assert "already exists" in capsys.readouterr().out and len(rows(db, "t")) == 1
    assert sci.main([str(data), "--db", str(db), "--apply", "--if-exists", "append"]) == 0
    assert len(rows(db, "t")) == 2
    other = write_csv(tmp_path / "t.csv", "a,c\n9,y\n")
    assert sci.main([str(other), "--db", str(db), "--apply", "--if-exists", "append"]) == 1
    assert "different columns" in capsys.readouterr().out and len(rows(db, "t")) == 2
    assert sci.main([str(other), "--db", str(db), "--apply", "--if-exists", "replace"]) == 0
    assert rows(db, "t") == [(9, "y")]


def test_multiple_files_and_custom_table(tmp_path):
    first = write_csv(tmp_path / "a.csv", "x\n1\n")
    second = write_csv(tmp_path / "b.csv", "y\n2\n3\n")
    db = tmp_path / "x.db"
    assert sci.main([str(first), str(second), "--db", str(db), "--apply"]) == 0
    assert rows(db, "a") == [(1,)] and rows(db, "b") == [(2,), (3,)]
    assert sci.main([str(first), "--db", str(db), "--apply", "--table", "renamed"]) == 0
    assert rows(db, "renamed") == [(1,)]


def test_bad_arguments_and_empty_files(tmp_path, capsys):
    one = write_csv(tmp_path / "a.csv", "x\n1\n")
    two = write_csv(tmp_path / "b.csv", "x\n1\n")
    with pytest.raises(SystemExit):
        sci.main([str(one), str(two), "--db", str(tmp_path / "x.db"), "--table", "t"])
    with pytest.raises(SystemExit):
        sci.main([str(tmp_path / "none.csv"), "--db", str(tmp_path / "x.db")])
    empty = write_csv(tmp_path / "e.csv", "")
    assert sci.main([str(empty), "--db", str(tmp_path / "x.db"), "--apply"]) == 1
    assert "empty file" in capsys.readouterr().out
