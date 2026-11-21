import json
import sqlite3

import pytest
import sqlite_query_cli as sq


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "t.db"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE people (id INTEGER PRIMARY KEY, name TEXT, score REAL)")
    con.executemany("INSERT INTO people VALUES (?,?,?)",
                    [(1, "Ada", 91.5), (2, "Bob", None), (3, "Cleopatra the Great", 70.0)])
    con.execute("CREATE VIEW top AS SELECT * FROM people WHERE score > 80")
    con.commit()
    con.close()
    return path


def test_render_table_aligns_numbers_and_shows_null():
    text = sq.render_table(["id", "name", "score"], [(1, "Ada", 91.5), (22, "Bob", None)])
    assert text.splitlines() == ["id | name | score", "---+------+------",
                                 " 1 | Ada  |  91.5", "22 | Bob  |  NULL"]


def test_render_table_truncates_long_values():
    text = sq.render_table(["x"], [("y" * 100,)])
    assert len(text.splitlines()[2]) == sq.MAX_WIDTH and text.endswith("…")


def test_other_formats():
    columns, rows = ["a", "b"], [(1, "x|y"), (2, None)]
    assert sq.render(columns, rows, "csv") == "a,b\n1,x|y\n2,"
    assert json.loads(sq.render(columns, rows, "json")) == [{"a": 1, "b": "x|y"},
                                                             {"a": 2, "b": None}]
    assert sq.render(columns, rows, "markdown").splitlines()[2] == "| 1 | x\\|y |"


def test_select_prints_table_and_count(db, capsys):
    assert sq.main([str(db), "SELECT name, score FROM people ORDER BY id"]) == 0
    out = capsys.readouterr().out
    assert "name" in out and "Ada" in out and "91.5" in out and "3 row(s)" in out


def test_limit_and_formats(db, capsys):
    assert sq.main([str(db), "SELECT id FROM people", "--limit", "2"]) == 0
    assert "3 row(s) (showing the first 2)" in capsys.readouterr().out
    assert sq.main([str(db), "SELECT id FROM people", "--format", "csv"]) == 0
    assert capsys.readouterr().out == "id\n1\n2\n3\n"


def test_tables_and_schema(db, capsys):
    assert sq.main([str(db), "--tables"]) == 0
    out = capsys.readouterr().out
    assert "people" in out and "3 rows" in out and "view" in out and "id, name, score" in out
    assert sq.main([str(db), "--schema"]) == 0
    assert "CREATE TABLE people" in capsys.readouterr().out


def test_database_is_read_only_by_default(db, capsys):
    assert sq.main([str(db), "DELETE FROM people"]) == 1
    assert "read-only" in capsys.readouterr().err
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM people").fetchone()[0] == 3


def test_write_is_a_dry_run_until_apply(db, capsys):
    assert sq.main([str(db), "DELETE FROM people WHERE id > 1", "--write"]) == 0
    assert "Dry run: 2 row(s) would change" in capsys.readouterr().out
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM people").fetchone()[0] == 3
    assert sq.main([str(db), "DELETE FROM people WHERE id > 1", "--write", "--apply"]) == 0
    assert "2 row(s) changed and saved" in capsys.readouterr().out
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM people").fetchone()[0] == 1


def test_sql_errors_are_friendly(db, capsys):
    assert sq.main([str(db), "SELEKT 1"]) == 1
    assert "SQL error" in capsys.readouterr().err
    assert sq.main([str(db), "SELECT * FROM ghost_table"]) == 1
    assert "no such table" in capsys.readouterr().err
    assert sq.main([str(db), "SELECT 1; SELECT 2"]) == 1
    assert "SQL error" in capsys.readouterr().err


def test_bad_arguments(db, tmp_path):
    with pytest.raises(SystemExit):
        sq.main([str(db)])
    with pytest.raises(SystemExit):
        sq.main([str(tmp_path / "none.db"), "SELECT 1"])
    not_a_db = tmp_path / "x.db"
    not_a_db.write_text("this is not sqlite")
    assert sq.main([str(not_a_db), "SELECT 1"]) == 1
