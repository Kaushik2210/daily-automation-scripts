from datetime import datetime

import pytest
import screen_time_report as stt

LOG = """time,app,title
2026-11-20T09:00:00,Code,main.py
2026-11-20T09:30:00,Chrome,Docs
2026-11-20T09:40:00,Code,main.py
2026-11-20T10:40:00,LockApp,Lock screen
2026-11-20T11:40:00,Code,main.py
2026-11-20T11:45:00,Slack,#chat
2026-11-21T09:00:00,Code,other.py
2026-11-21T09:10:00,Code,other.py
"""


def entries(tmp_path, idle_gap=60):
    log = tmp_path / "w.csv"
    log.write_text(LOG)
    return list(stt.durations(stt.read_rows(log), idle_gap, stt.IDLE_APPS))


def test_each_row_lasts_until_the_next_row(tmp_path):
    seconds = {(a, s.day, s.hour, s.minute): sec for s, a, _, sec in entries(tmp_path)}
    assert seconds[("Code", 20, 9, 0)] == 30 * 60
    assert seconds[("Chrome", 20, 9, 30)] == 10 * 60
    assert seconds[("Code", 20, 9, 40)] == 60 * 60
    assert seconds[("Code", 20, 11, 40)] == 5 * 60
    assert seconds[("Code", 21, 9, 0)] == 10 * 60


def test_lock_screens_and_the_last_row_are_not_counted(tmp_path):
    apps = [(s.day, a) for s, a, _, _ in entries(tmp_path)]
    assert (20, "LockApp") not in apps
    assert apps.count((21, "Code")) == 1  # the final row of the log has no end time
    assert len(apps) == 6


def test_gaps_longer_than_the_idle_limit_are_capped(tmp_path):
    capped = {(a, s.hour, s.minute): sec for s, a, _, sec in entries(tmp_path, idle_gap=5)}
    assert capped[("Code", 9, 0)] == 5 * 60 and capped[("Code", 9, 40)] == 5 * 60
    assert capped[("Chrome", 9, 30)] == 5 * 60


def test_human():
    assert stt.human(59 * 60) == "59m" and stt.human(3600 + 5 * 60) == "1h 05m"
    assert stt.human(20) == "0m"


def test_summarise_by_app_and_title(tmp_path):
    items = entries(tmp_path)
    by_app = stt.summarise(items)
    assert by_app["2026-11-20"]["Code"] == (30 + 60 + 5) * 60
    assert by_app["2026-11-20"]["Chrome"] == 10 * 60
    assert "Code: main.py" in stt.summarise(items, by_title=True)["2026-11-20"]


def test_cli_report_and_filters(tmp_path, capsys):
    log = tmp_path / "w.csv"
    log.write_text(LOG)
    assert stt.main([str(log), "--idle-gap", "60"]) == 0
    out = capsys.readouterr().out
    assert "2026-11-20  total 2h 45m" in out and "2026-11-21  total 10m" in out
    assert "All 2 days" in out and "lock screens count as idle" in out
    assert stt.main([str(log), "--date", "2026-11-21", "--idle-gap", "60"]) == 0
    assert "2026-11-20" not in capsys.readouterr().out
    assert stt.main([str(log), "--date", "2026-01-01"]) == 1
    assert stt.main([str(log), "--ignore", "code,chrome,slack"]) == 1


def test_bad_arguments_and_rows(tmp_path):
    log = tmp_path / "w.csv"
    log.write_text("time,app,title\nnot a date,Code,x\n")
    assert stt.read_rows(log) == []
    assert stt.main([str(log)]) == 1
    with pytest.raises(SystemExit):
        stt.main([str(log), "--date", "tomorrow"])
    with pytest.raises(SystemExit):
        stt.main([str(tmp_path / "none.csv")])


def test_rows_are_sorted(tmp_path):
    log = tmp_path / "w.csv"
    log.write_text("time,app,title\n2026-11-21T09:05:00,B,\n2026-11-21T09:00:00,A,\n"
                   "2026-11-21T09:06:00,C,\n")
    rows = stt.read_rows(log)
    assert [r[1] for r in rows] == ["A", "B", "C"] and rows[0][0] == datetime(2026, 11, 21, 9, 0)
