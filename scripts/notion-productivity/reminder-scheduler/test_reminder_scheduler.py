from datetime import datetime, timedelta

import pytest
import reminder_scheduler as rs

NOW = datetime(2026, 11, 21, 9, 0, 0)


@pytest.mark.parametrize("text,expected", [
    ("25m", NOW + timedelta(minutes=25)), ("+25m", NOW + timedelta(minutes=25)),
    ("in 25m", NOW + timedelta(minutes=25)),
    ("1h30m", NOW + timedelta(hours=1, minutes=30)), ("90s", NOW + timedelta(seconds=90)),
    ("1.5h", NOW + timedelta(minutes=90)),
    ("15:30", datetime(2026, 11, 21, 15, 30)), ("09:00", datetime(2026, 11, 22, 9, 0)),
    ("8:15", datetime(2026, 11, 22, 8, 15)),
    ("2026-11-22 07:45", datetime(2026, 11, 22, 7, 45))])
def test_parse_when(text, expected):
    assert rs.parse_when(text, NOW) == expected


@pytest.mark.parametrize("bad", ["", "soon", "25", "25x", "24:00", "12:60", "0m",
                                 "2026-11-20 09:00"])
def test_parse_when_rejects(bad):
    with pytest.raises(ValueError):
        rs.parse_when(bad, NOW)


def test_read_file(tmp_path):
    path = tmp_path / "r.txt"
    path.write_text("# comment\n\n+25m Stand up\nin 1h Call\n15:30 Timesheet\n18:00\n")
    assert rs.read_file(path, NOW) == [
        (NOW + timedelta(minutes=25), "Stand up"), (NOW + timedelta(hours=1), "Call"),
        (datetime(2026, 11, 21, 15, 30), "Timesheet"), (datetime(2026, 11, 21, 18, 0), "Reminder")]
    path.write_text("+25m ok\nsoon bad\n")
    with pytest.raises(ValueError, match="line 2"):
        rs.read_file(path, NOW)


def test_run_waits_in_time_order_and_fires():
    clock = [NOW]
    fired, slept = [], []

    def now():
        return clock[0]

    def sleep(seconds):
        slept.append(seconds)
        clock[0] += timedelta(seconds=seconds)

    reminders = [(NOW + timedelta(seconds=5), "second"), (NOW + timedelta(seconds=2), "first")]
    assert rs.run(reminders, now=now, sleep=sleep, out=fired.append) == 2
    assert [f.split("REMINDER: ")[1] for f in fired] == ["first", "second"]
    assert sum(slept) >= 5 and max(slept) <= 1.0


def test_cli_plan_and_errors(tmp_path, capsys):
    assert rs.main(["25m", "Stand", "up", "--plan", "--now", "2026-11-21 09:00"]) == 0
    out = capsys.readouterr().out
    assert "1 reminder(s)" in out and "Sat 21 Nov 09:25  (in 0h 25m)  Stand up" in out
    assert "Plan only" in out
    path = tmp_path / "r.txt"
    path.write_text("+1h Call\n15:30 Timesheet\n")
    assert rs.main(["--file", str(path), "--plan", "--now", "2026-11-21 09:00"]) == 0
    out = capsys.readouterr().out
    assert out.index("Call") < out.index("Timesheet") and "(in 6h 30m)" in out
    assert rs.main(["soon", "--plan"]) == 1
    assert "Can't schedule that" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        rs.main([])
    with pytest.raises(SystemExit):
        rs.main(["5m", "--now", "yesterday"])


def test_short_real_reminder(capsys):
    assert rs.main(["1s", "ping"]) == 0
    out = capsys.readouterr().out
    assert "REMINDER: ping" in out and "Done: 1 reminder(s) shown." in out
