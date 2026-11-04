from datetime import datetime, timedelta

import countdown_timer as ct
import pytest

NOW = datetime(2026, 1, 1, 9, 0, 0)


def test_parse_durations():
    assert ct.parse_target("90s", NOW) == NOW + timedelta(seconds=90)
    assert ct.parse_target("1h30m", NOW) == NOW + timedelta(hours=1, minutes=30)
    assert ct.parse_target("2d 3h", NOW) == NOW + timedelta(days=2, hours=3)


def test_parse_dates():
    assert ct.parse_target("2026-12-25", NOW) == datetime(2026, 12, 25)
    assert ct.parse_target("2026-12-25 18:30", NOW) == datetime(2026, 12, 25, 18, 30)
    with pytest.raises(ValueError):
        ct.parse_target("next friday", NOW)
    with pytest.raises(ValueError):
        ct.parse_target("5x", NOW)


def test_describe_pluralisation():
    assert ct.describe(timedelta(days=1, hours=2, minutes=1, seconds=5)) == (
        "1 day, 2 hours, 1 minute, 5 seconds")
    assert ct.describe(timedelta(0)) == "0 seconds"
    assert ct.describe(timedelta(seconds=-61)) == "1 minute, 1 second"


def test_message_future_and_past():
    assert ct.message(datetime(2026, 1, 2, 9, 0), NOW).startswith("1 day until 2026-01-02")
    past = ct.message(datetime(2025, 12, 31, 8, 0), NOW)
    assert past == "2025-12-31 08:00:00 was 1 day, 1 hour ago"


def test_cli_with_fixed_now(capsys):
    ct.main(["2026-01-10", "--now", "2026-01-01 09:00"])
    assert capsys.readouterr().out.startswith("8 days, 15 hours until 2026-01-10")
    with pytest.raises(SystemExit):
        ct.main(["whenever"])
