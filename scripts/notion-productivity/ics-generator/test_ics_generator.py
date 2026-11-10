from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import ics_generator as ig
import pytest

NOW = datetime(2026, 11, 1, 8, 0, tzinfo=UTC)


def test_parse_when_accepts_dates_and_datetimes():
    assert ig.parse_when("2026-11-16") == date(2026, 11, 16)
    assert ig.parse_when("2026-11-16 09:30") == datetime(2026, 11, 16, 9, 30)
    assert ig.parse_when("2026-11-16T09:30") == datetime(2026, 11, 16, 9, 30)
    with pytest.raises(ValueError):
        ig.parse_when("tomorrow")


def test_escape_and_fold():
    assert ig.escape("a,b;c\\d\nnext") == "a\\,b\\;c\\\\d\\nnext"
    long_line = "SUMMARY:" + "é" * 80
    folded = ig.fold(long_line).split("\r\n")
    assert len(folded) > 1 and all(len(part.encode()) <= 75 for part in folded)
    assert folded[1].startswith(" ")
    assert "".join([folded[0]] + [p[1:] for p in folded[1:]]) == long_line  # unfolds cleanly
    assert ig.fold("short") == "short"


def event(row, **kw):
    options = {"zone": None, "to_utc": False, "minutes": 60, "alarm": 0, "now": NOW}
    return "\r\n".join(ig.make_event(row, **{**options, **kw}))


def test_timed_event_defaults_and_optional_fields():
    text = event({"title": "Standup", "start": "2026-11-16 09:30", "location": "Zoom, room 2"})
    assert "DTSTART:20261116T093000" in text and "DTEND:20261116T103000" in text
    assert "DTSTAMP:20261101T080000Z" in text and "LOCATION:Zoom\\, room 2" in text
    assert "DESCRIPTION" not in text and text.startswith("BEGIN:VEVENT")
    assert event({"title": "Standup", "start": "2026-11-16 09:30"}).count("UID:") == 1


def test_uid_is_stable_for_the_same_event():
    row = {"title": "A", "start": "2026-11-16 09:30"}
    assert event(row) == event(row)
    assert event(row) != event({"title": "B", "start": "2026-11-16 09:30"})


def test_all_day_events_use_date_values_and_end_the_next_day():
    text = event({"Summary": "Launch", "Date": "2026-11-20"})
    assert "DTSTART;VALUE=DATE:20261120" in text and "DTEND;VALUE=DATE:20261121" in text
    assert "VALARM" not in event({"title": "x", "start": "2026-11-20"}, alarm=15)


def test_timezone_modes():
    row = {"title": "Call", "start": "2026-11-16 09:30", "end": "2026-11-16 10:00"}
    zone = ZoneInfo("America/New_York")
    assert "DTSTART;TZID=America/New_York:20261116T093000" in event(row, zone=zone)
    utc = event(row, zone=zone, to_utc=True)
    assert "DTSTART:20261116T143000Z" in utc and "DTEND:20261116T150000Z" in utc


def test_alarm_and_validation_errors():
    assert "TRIGGER:-PT15M" in event({"title": "x", "start": "2026-11-16 09:00"}, alarm=15)
    for row, message in [({"title": "", "start": "2026-11-16"}, "needs a title"),
                         ({"title": "x", "start": "2026-11-16", "end": "2026-11-16 10:00"},
                          "both be dates"),
                         ({"title": "x", "start": "2026-11-16 10:00", "end": "2026-11-16 09:00"},
                          "ends before"),
                         ({"title": "x", "start": "soon"}, "Invalid")]:
        with pytest.raises(ValueError, match=message):
            ig.make_event(row, None, False, 60, 0, NOW)


def test_build_calendar_is_a_valid_vcalendar_and_reports_bad_rows():
    rows = [{"title": "Good", "start": "2026-11-16 09:00"}, {"title": "Bad", "start": "never"}]
    text, problems = ig.build_calendar(rows, now=NOW, name="Team, 2026")
    assert text.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\n") and text.endswith(
        "END:VEVENT\r\nEND:VCALENDAR\r\n")
    assert text.count("BEGIN:VEVENT") == 1 and "X-WR-CALNAME:Team\\, 2026" in text
    assert [number for number, _ in problems] == [3]


def test_cli_prints_or_writes_and_refuses_to_overwrite(tmp_path, capsys):
    src, out = tmp_path / "e.csv", tmp_path / "e.ics"
    src.write_text("title,start,end\nA,2026-11-16 09:00,2026-11-16 10:00\nB,2026-11-17,\n")
    assert ig.main([str(src), "--stamp", "2026-11-01T08:00"]) == 0
    printed = capsys.readouterr().out
    assert printed.count("BEGIN:VEVENT") == 2 and "DTSTAMP:20261101T080000Z" in printed
    assert ig.main([str(src), "--out", str(out)]) == 0
    assert out.read_bytes().count(b"\r\n") > 10 and "Wrote 2 event(s)" in capsys.readouterr().out
    assert ig.main([str(src), "--out", str(out)]) == 1


def test_cli_partial_failures_and_argument_errors(tmp_path, capsys):
    src = tmp_path / "e.csv"
    src.write_text("title,start\nGood,2026-11-16 09:00\n,2026-11-17\n")
    assert ig.main([str(src)]) == 1  # exit 1 because one row was skipped
    captured = capsys.readouterr()
    assert "row 3 skipped" in captured.err and captured.out.count("BEGIN:VEVENT") == 1
    for bad in (["--utc"], ["--tz", "Mars/Base"]):
        with pytest.raises(SystemExit):
            ig.main([str(src), *bad])
    src.write_text("title,start\n,\n")
    assert ig.main([str(src)]) == 1
