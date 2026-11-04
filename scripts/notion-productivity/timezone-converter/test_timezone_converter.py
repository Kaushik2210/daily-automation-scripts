from datetime import date, datetime, time

import pytest
import timezone_converter as tz


def test_parse_clock_formats():
    assert tz.parse_clock("14:30") == time(14, 30)
    assert tz.parse_clock("2:30pm") == time(14, 30)
    assert tz.parse_clock("9 AM") == time(9, 0)
    with pytest.raises(ValueError):
        tz.parse_clock("noonish")


def test_convert_known_offsets_winter_and_summer():
    winter = datetime(2026, 1, 15, 12, 0)
    (_, ny), (_, tokyo) = tz.convert(winter, "UTC", ["America/New_York", "Asia/Tokyo"])
    assert (ny.hour, tokyo.hour) == (7, 21)
    summer = datetime(2026, 7, 15, 12, 0)
    (_, london), = tz.convert(summer, "UTC", ["Europe/London"])
    assert london.hour == 13  # British Summer Time


def test_day_note():
    a = datetime(2026, 1, 15, 23, 0)
    (_, kolkata), = tz.convert(a, "UTC", ["Asia/Kolkata"])
    assert tz.day_note(a, kolkata) == " (+1 day)"
    assert tz.day_note(a, a) == ""


def test_find_zones():
    assert "Europe/London" in tz.find_zones("london")
    assert "America/New_York" in tz.find_zones("new york")


def test_cli_output_and_errors(capsys):
    tz.main(["12:00", "--from", "UTC", "--to", "Asia/Kolkata", "--date", "2026-01-15"])
    out = capsys.readouterr().out
    assert "Thu 2026-01-15 17:30  Asia/Kolkata (+0530)" in out
    with pytest.raises(SystemExit):
        tz.main(["12:00", "--to", "Mars/Olympus"])
    assert tz.main(["--find", "zzzzqq"]) == 1
    assert date.fromisoformat("2026-01-15").weekday() == 3
