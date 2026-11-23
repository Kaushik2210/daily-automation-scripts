import sqlite3

import log_to_sqlite as lts
import pytest

ACCESS = ('203.0.113.9 - - [10/Nov/2026:09:00:06 +0000] "POST /api/orders HTTP/1.1" 500 123 '
          '"-" "Mozilla/5.0 (X11)"')
APP = "2026-11-10 08:40:09,475 WARNING  [api] disk usage at 64%"


def test_parse_access_line():
    kind, fields = lts.parse_line(ACCESS)
    assert kind == "access" and fields["ip"] == "203.0.113.9"
    assert fields["ts"] == "2026-11-10T09:00:06" and fields["method"] == "POST"
    assert fields["path"] == "/api/orders" and fields["protocol"] == "HTTP/1.1"
    assert (fields["status"], fields["bytes"], fields["agent"]) == (500, 123, "Mozilla/5.0 (X11)")


def test_access_line_variants():
    _, plain = lts.parse_line('1.2.3.4 - - [01/Jan/2026:00:00:01 +0000] "GET / HTTP/1.0" 304 -')
    assert plain["bytes"] == 0 and plain["agent"] == "" and plain["status"] == 304
    _, odd = lts.parse_line('1.2.3.4 - - [01/Jan/2026:00:00:01 +0000] "-" 400 0')
    assert odd["method"] == "-" and odd["path"] == ""


def test_parse_app_lines():
    kind, fields = lts.parse_line(APP)
    assert kind == "app" and fields == {"ts": "2026-11-10T08:40:09", "level": "WARNING",
                                        "component": "api", "message": "disk usage at 64%"}
    assert lts.parse_line("2026-11-10T08:40:09.5 WARN no component here")[1]["level"] == "WARNING"
    assert lts.parse_line("2026-11-10 08:40:09 ERR boom")[1]["level"] == "ERROR"
    assert lts.parse_line("2026-11-10 08:40:09 CHATTER not a level") is None


def test_unrecognised_lines():
    assert lts.parse_line("just some text") is None
    assert lts.parse_line("") is None


def test_load_joins_stack_traces_and_counts_unparsed(tmp_path):
    log = tmp_path / "mixed.log"
    log.write_text("\n".join([
        APP, "2026-11-10 09:00:00,000 ERROR  [db] query failed",
        "Traceback (most recent call last):", '  File "x.py", line 3, in run', "KeyError: 'id'",
        "garbage line", ACCESS, ""]))
    access, app, unparsed = lts.load(log)
    assert len(access) == 1 and len(app) == 2 and unparsed == 1
    assert access[0][0] == 7 and app[1][0] == 2
    assert app[1][1]["message"].startswith("query failed\nTraceback")
    assert app[1][1]["message"].endswith("KeyError: 'id'")


def rows(db, sql):
    with sqlite3.connect(db) as con:
        return con.execute(sql).fetchall()


def test_cli_dry_run_then_apply_and_append(tmp_path, capsys):
    log = tmp_path / "a.log"
    log.write_text("\n".join([ACCESS, APP, "2026-11-10 09:00:00 ERROR [db] failed"]))
    db = tmp_path / "logs.db"
    assert lts.main([str(log), "--db", str(db)]) == 0
    out = capsys.readouterr().out
    assert "1 access line(s), 2 application line(s)" in out and "Dry run" in out
    assert not db.exists()
    assert lts.main([str(log), "--db", str(db), "--apply"]) == 0
    assert rows(db, "SELECT COUNT(*) FROM app_logs") == [(2,)]
    assert rows(db, "SELECT status, path FROM access_logs") == [(500, "/api/orders")]
    out = capsys.readouterr().out
    assert "access_logs: 1 row(s)" in out and "status codes: 500 x1" in out
    lts.main([str(log), "--db", str(db), "--apply"])
    assert rows(db, "SELECT COUNT(*) FROM app_logs") == [(4,)]  # appended
    lts.main([str(log), "--db", str(db), "--apply", "--replace"])
    assert rows(db, "SELECT COUNT(*) FROM app_logs") == [(2,)]


def test_nothing_recognised_and_bad_arguments(tmp_path, capsys):
    junk = tmp_path / "j.log"
    junk.write_text("nothing useful\n")
    assert lts.main([str(junk), "--db", str(tmp_path / "x.db")]) == 1
    assert "1 not recognised" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        lts.main([str(tmp_path / "none.log"), "--db", str(tmp_path / "x.db")])
