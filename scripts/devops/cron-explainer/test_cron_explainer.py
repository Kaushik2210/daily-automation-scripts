from datetime import datetime

import cron_explainer as ce
import pytest


@pytest.mark.parametrize("expression,text", [
    ("* * * * *", "Every minute, every day"),
    ("*/15 * * * *", "Every 15 minutes, every day"),
    ("0 * * * *", "At the start of every hour, every day"),
    ("30 * * * *", "At minute 30 of every hour, every day"),
    ("0 2 * * *", "At 02:00, every day"),
    ("30 8 * * 1-5", "At 08:30, on Monday through Friday"),
    ("0 9,17 * * MON,WED,FRI", "At 09:00 and 17:00, on Monday, Wednesday and Friday"),
    ("0 0 1 * *", "At 00:00, on day 1 of the month"),
    ("*/10 9-17 * * *", "Every 10 minutes between 09:00 and 17:59, every day"),
    ("0 12 * jan-mar *", "At 12:00, every day in January through March"),
    ("15 4 * * 0,6", "At 04:15, on Sunday and Saturday"),
    ("0 0 * * 7", "At 00:00, on Sunday"),
    ("0 8 1,15 * 1",
     "At 08:00, on day 1 and 15 of the month or on Monday "
     "(when both a day of the month and a weekday are given, either one matches)"),
    ("@daily", "At 00:00, every day"),
    ("@hourly", "At the start of every hour, every day"),
    ("@reboot", "once, when the system starts"),
])
def test_explain(expression, text):
    assert ce.explain(expression)[0] == text


@pytest.mark.parametrize("expression", ["* * * *", "61 * * * *", "* 24 * * *", "a b c d e",
                                        "*/0 * * * *", "* * 0 * *", "5-2 * * * *"])
def test_invalid_expressions(expression):
    with pytest.raises(ValueError):
        ce.explain(expression)


def test_parse_field():
    assert ce.parse_field("*/20", 0) == ([0, 20, 40], False)
    assert ce.parse_field("1-5/2", 1) == ([1, 3, 5], False)
    assert ce.parse_field("mon-wed", 4) == ([1, 2, 3], False)
    assert ce.parse_field("7", 4) == ([0], False) and ce.parse_field("*", 2)[1] is True


def test_next_runs_daily_and_weekdays():
    parsed = ce.explain("30 8 * * 1-5")[1]
    runs = ce.next_runs(parsed, datetime(2026, 11, 20, 9, 0), 3)  # a Friday after 08:30
    assert [r.strftime("%a %d %H:%M") for r in runs] == ["Mon 23 08:30", "Tue 24 08:30",
                                                         "Wed 25 08:30"]
    same_day = ce.next_runs(parsed, datetime(2026, 11, 18, 8, 0), 1)
    assert same_day == [datetime(2026, 11, 18, 8, 30)]


def test_next_runs_every_15_minutes_is_strictly_after_start():
    parsed = ce.explain("*/15 * * * *")[1]
    runs = ce.next_runs(parsed, datetime(2026, 11, 18, 9, 30), 3)
    assert [r.strftime("%H:%M") for r in runs] == ["09:45", "10:00", "10:15"]


def test_day_of_month_or_weekday_semantics():
    parsed = ce.explain("0 8 1,15 * 1")[1]  # the 1st, the 15th, or any Monday
    runs = ce.next_runs(parsed, datetime(2026, 11, 1, 9, 0), 4)
    assert [r.strftime("%d") for r in runs] == ["02", "09", "15", "16"]


def test_leap_day_is_found_years_ahead():
    parsed = ce.explain("0 0 29 2 *")[1]
    assert ce.next_runs(parsed, datetime(2026, 11, 18, 0, 0), 1) == [datetime(2028, 2, 29, 0, 0)]


def test_crontab_file_and_cli(tmp_path, capsys):
    cron = tmp_path / "crontab"
    cron.write_text("# comment\nMAILTO=me@example.com\n0 2 * * * /bin/backup\n"
                    "@weekly /bin/clean up\n"
                    "bad line here\n")
    assert ce.cron_lines(cron).__next__() == ("0 2 * * *", "/bin/backup")
    assert ce.main(["--file", str(cron), "--from", "2026-11-18 09:30", "--next", "2"]) == 1
    out = capsys.readouterr().out
    assert "At 02:00, every day" in out
    assert "next: Thu 19 Nov 2026 02:00; Fri 20 Nov 2026 02:00" in out
    assert "@weekly   /bin/clean up" in out and "At 00:00, on Sunday" in out
    assert "! expected 5 fields" in out
    assert ce.main(["*/5 * * * *", "--from", "2026-11-18 09:30", "--next", "1"]) == 0
    with pytest.raises(SystemExit):
        ce.main([])
    with pytest.raises(SystemExit):
        ce.main(["* * * * *", "--from", "tomorrow"])
