from datetime import datetime

import pomodoro_timer as pt


def test_schedule_shape():
    schedule = pt.build_schedule(25, 5, 15, sessions=4)
    assert [m for _, m in schedule] == [25, 5, 25, 5, 25, 5, 25, 15]
    assert schedule[0][0] == "Focus 1/4" and schedule[-1][0] == "Long break"


def test_schedule_rounds_repeat_with_long_breaks():
    schedule = pt.build_schedule(10, 2, 8, sessions=2, rounds=2)
    assert [label for label, _ in schedule].count("Long break") == 2
    assert len(schedule) == 8


def test_clock_plan_times():
    rows, end = pt.clock_plan(pt.build_schedule(25, 5, 15, 2), datetime(2026, 1, 5, 9, 0))
    assert [r[0] for r in rows] == ["09:00", "09:25", "09:30", "09:55"]
    assert end.strftime("%H:%M") == "10:10"


def test_format_remaining():
    assert pt.format_remaining(65) == "01:05" and pt.format_remaining(0) == "00:00"


def test_plan_cli_and_seconds_run(monkeypatch, capsys):
    pt.main(["--plan", "--start", "08:30", "--sessions", "2"])
    out = capsys.readouterr().out
    assert out.startswith("08:30  Focus 1/2") and "Ends at 09:40" in out
    sleeps = []
    monkeypatch.setattr(pt.time, "sleep", sleeps.append)
    assert pt.main(["--unit", "seconds", "--focus", "2", "--break", "1", "--long-break", "1",
                    "--sessions", "2", "--no-bell"]) == 0
    assert len(sleeps) == 2 + 1 + 2 + 1
    assert "All rounds complete." in capsys.readouterr().out
