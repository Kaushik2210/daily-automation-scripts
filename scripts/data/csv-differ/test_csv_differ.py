import csv_differ as cd
import pytest

OLD = "id,name,status,score\n1,Ada,active,90\n2,Bob,active,70\n3,Cy,inactive,60\n"
NEW = "id,name,status,score\n1,Ada,active,90.0\n2,Bob,inactive,75\n4,Di,active,80\n"


def write(path, text):
    path.write_text(text)
    return str(path)


def tables(old=OLD, new=NEW, tmp=None):
    parsed = []
    for text in (old, new):
        lines = [r.split(",") for r in text.strip().splitlines()]
        parsed.append(cd.index_rows(lines[0], lines[1:], ["id"])[0])
    return parsed


def test_added_removed_changed():
    old, new = tables()
    added, removed, changed = cd.diff(old, new, ["id"], set(), loose=False)
    assert added == [("4",)] and removed == [("3",)]
    assert changed == [(("1",), [("score", "90", "90.0")]),
                       (("2",), [("status", "active", "inactive"), ("score", "70", "75")])]


def test_loose_mode_ignores_formatting_differences():
    old, new = tables()
    _, _, changed = cd.diff(old, new, ["id"], set(), loose=True)
    assert [k for k, _ in changed] == [("2",)]
    assert cd.same(" Yes ", "yes", True) and not cd.same("Yes", "yes", False)
    assert cd.same("66", "66.0", True) and not cd.same("66", "67", True)


def test_ignore_columns():
    old, new = tables()
    _, _, changed = cd.diff(old, new, ["id"], {"score"}, loose=False)
    assert changed == [(("2",), [("status", "active", "inactive")])]


def test_duplicate_keys_are_reported():
    header = ["id", "v"]
    table, duplicates = cd.index_rows(header, [["1", "a"], ["1", "b"], ["2", "c"]], ["id"])
    assert duplicates == [("1",)] and table[("1",)]["v"] == "a"


def test_composite_keys():
    header = ["a", "b", "v"]
    old, _ = cd.index_rows(header, [["1", "x", "1"], ["1", "y", "2"]], ["a", "b"])
    new, _ = cd.index_rows(header, [["1", "x", "1"], ["1", "y", "9"]], ["a", "b"])
    assert cd.diff(old, new, ["a", "b"], set(), False)[2] == [(("1", "y"), [("v", "2", "9")])]


def test_cli_text_report(tmp_path, capsys):
    old, new = write(tmp_path / "o.csv", OLD), write(tmp_path / "n.csv", NEW)
    assert cd.main([old, new, "--key", "id"]) == 1
    out = capsys.readouterr().out
    assert "o.csv (3 rows) -> n.csv (3 rows), key: id" in out
    assert "Added (1):\n  + 4  name=Di, status=active, score=80" in out
    assert "Removed (1):\n  - 3  name=Cy" in out
    assert "~ 2\n      status: 'active' -> 'inactive'" in out
    assert "1 added, 1 removed, 2 changed." in out
    assert cd.main([old, new, "--loose"]) == 1
    assert "2 changed" not in capsys.readouterr().out


def test_cli_csv_format_and_no_differences(tmp_path, capsys):
    old, new = write(tmp_path / "o.csv", OLD), write(tmp_path / "n.csv", NEW)
    assert cd.main([old, new, "--format", "csv"]) == 1
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "change,key,column,old,new" and "added,4,,," in out
    assert "changed,2,status,active,inactive" in out
    assert cd.main([old, old]) == 0
    assert "No differences." in capsys.readouterr().out


def test_column_changes_and_errors(tmp_path, capsys):
    old = write(tmp_path / "o.csv", "id,a\n1,x\n")
    new = write(tmp_path / "n.csv", "id,a,b\n1,x,y\n")
    assert cd.main([old, new]) == 1
    assert "Columns: +b  --" in capsys.readouterr().out
    dup = write(tmp_path / "d.csv", "id,a\n1,x\n1,y\n")
    assert cd.main([dup, new]) == 2
    assert "not unique" in capsys.readouterr().err
    empty = write(tmp_path / "e.csv", "")
    assert cd.main([empty, new]) == 2
    with pytest.raises(SystemExit):
        cd.main([old, new, "--key", "zzz"])
    with pytest.raises(SystemExit):
        cd.main([old, str(tmp_path / "none.csv")])
