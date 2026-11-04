from datetime import datetime

import break_reminder as br
import pytest


def test_reminder_times_start_after_first_interval():
    start = datetime(2026, 1, 5, 9, 0)
    times = br.reminder_times(start, 30, 120)
    assert [t.strftime("%H:%M") for t in times] == ["09:30", "10:00", "10:30", "11:00"]
    assert br.reminder_times(start, 50, 60) == [datetime(2026, 1, 5, 9, 50)]


def test_message_rotation_and_custom():
    assert br.pick_message(0) == br.DEFAULT_MESSAGES[0]
    assert br.pick_message(len(br.DEFAULT_MESSAGES)) == br.DEFAULT_MESSAGES[0]
    assert br.pick_message(3, "Hydrate!") == "Hydrate!"


def test_plan_output(capsys):
    assert br.main(["--plan", "--start", "09:00", "--every", "45", "--total", "135"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("09:45  ") and out[2].startswith("11:15  ")
    assert out[-1] == "3 reminder(s) over 135 minutes, every 45 minutes."


def test_run_with_seconds_calls_sleep_each_time(monkeypatch, capsys):
    sleeps = []
    monkeypatch.setattr(br.time, "sleep", sleeps.append)
    assert br.main(["--every", "2", "--total", "6", "--unit", "seconds", "--no-bell",
                    "--message", "Move!"]) == 0
    assert sleeps == [2, 2, 2]
    assert capsys.readouterr().out.count("Move!") == 3


def test_bad_arguments():
    with pytest.raises(SystemExit):
        br.main(["--every", "60", "--total", "30"])
    with pytest.raises(SystemExit):
        br.main(["--start", "9am", "--plan"])
