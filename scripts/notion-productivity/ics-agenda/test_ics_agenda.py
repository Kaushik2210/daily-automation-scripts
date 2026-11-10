from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import ics_agenda as ia
import pytest

UTC = ZoneInfo("UTC")


def calendar(*events):
    body = "\r\n".join(line for event in events for line in
                       ["BEGIN:VEVENT", *event, "END:VEVENT"])
    return f"BEGIN:VCALENDAR\r\nVERSION:2.0\r\n{body}\r\nEND:VCALENDAR\r\n"


def agenda(text, day, days=1, zone=UTC):
    return ia.build_agenda(ia.parse_events(text), day, days, zone)


def lines(result, day):
    return [text for _, _, text in result[day]]


def test_unfold_unescape_and_duration():
    assert ia.unfold("A:long\r\n  line\r\nB:x") == ["A:long line", "B:x"]
    assert ia.unescape("Lunch\\, with\\nAlice\\; ok") == "Lunch, with\nAlice; ok"
    assert ia.parse_duration("PT1H30M") == timedelta(hours=1, minutes=30)
    assert ia.parse_duration("P1DT2H") == timedelta(days=1, hours=2)
    assert ia.parse_duration("nonsense") == timedelta(0)


def test_parse_value_kinds():
    assert ia.parse_value("20261116", {}) == (date(2026, 11, 16), None)
    assert ia.parse_value("20261120", {"VALUE": "DATE"})[0] == date(2026, 11, 20)
    assert ia.parse_value("20261116T093000", {}) == (datetime(2026, 11, 16, 9, 30), None)
    dt, zone = ia.parse_value("20261116T123000Z", {})
    assert dt.hour == 12 and zone is not None
    assert ia.parse_value("20261116T150000", {"TZID": "Europe/London"})[1].key == "Europe/London"
    assert ia.parse_value("20261116T150000", {"TZID": "Not/AZone"})[1] is None


def test_single_events_sorted_with_all_day_first():
    text = calendar(
        ["DTSTART:20261116T140000", "DTEND:20261116T150000", "SUMMARY:Afternoon",
         "LOCATION:Room 2"],
        ["DTSTART:20261116T090000", "DTEND:20261116T093000", "SUMMARY:Morning"],
        ["DTSTART;VALUE=DATE:20261116", "DTEND;VALUE=DATE:20261117", "SUMMARY:Holiday"])
    result = agenda(text, date(2026, 11, 16))
    assert lines(result, date(2026, 11, 16)) == [
        "all day     Holiday", "09:00-09:30  Morning", "14:00-15:00  Afternoon  @ Room 2"]
    assert lines(agenda(text, date(2026, 11, 17)), date(2026, 11, 17)) == []


def test_multi_day_all_day_event_appears_each_day():
    text = calendar(["DTSTART;VALUE=DATE:20261116", "DTEND;VALUE=DATE:20261119", "SUMMARY:Trip"])
    result = agenda(text, date(2026, 11, 15), days=5)
    shown = [day.day for day, items in result.items() if items]
    assert shown == [16, 17, 18]


def test_utc_times_are_converted_to_the_display_zone():
    text = calendar(["DTSTART:20261116T123000Z", "DTEND:20261116T133000Z", "SUMMARY:Lunch"])
    assert lines(agenda(text, date(2026, 11, 16), zone=ZoneInfo("Asia/Kolkata")),
                 date(2026, 11, 16)) == ["18:00-19:00  Lunch"]
    local = calendar(["DTSTART;TZID=America/New_York:20261116T090000", "SUMMARY:Call"])
    assert lines(agenda(local, date(2026, 11, 16)), date(2026, 11, 16)) == ["14:00        Call"]


def test_daily_rule_with_count_and_exdate():
    text = calendar(["DTSTART:20261116T093000", "DTEND:20261116T094500", "SUMMARY:Standup",
                     "RRULE:FREQ=DAILY;COUNT=4", "EXDATE:20261118T093000"])
    result = agenda(text, date(2026, 11, 15), days=7)
    days = [day.day for day, items in result.items() if items]
    assert days == [16, 17, 19]  # 4 occurrences, the 18th is excluded


def test_weekly_rule_with_byday_and_until():
    text = calendar(["DTSTART:20261116T150000", "DTEND:20261116T160000", "SUMMARY:Review",
                     "RRULE:FREQ=WEEKLY;BYDAY=MO,TH;UNTIL=20261126T235959"])
    result = agenda(text, date(2026, 11, 16), days=14)
    days = [day.day for day, items in result.items() if items]
    assert days == [16, 19, 23, 26]  # nothing after the UNTIL date


def test_weekly_interval_monthly_and_yearly_rules():
    biweekly = calendar(["DTSTART:20261116T090000", "SUMMARY:B", "RRULE:FREQ=WEEKLY;INTERVAL=2"])
    days = [d for d, i in agenda(biweekly, date(2026, 11, 16), 30).items() if i]
    assert days == [date(2026, 11, 16), date(2026, 11, 30), date(2026, 12, 14)]  # every 2nd week
    monthly = calendar(["DTSTART;VALUE=DATE:20260131", "SUMMARY:M", "RRULE:FREQ=MONTHLY;COUNT=3"])
    hits = [d for d, i in agenda(monthly, date(2026, 1, 1), 31 * 5).items() if i]
    assert hits == [date(2026, 1, 31), date(2026, 3, 31), date(2026, 5, 31)]  # skips short months
    yearly = calendar(["DTSTART;VALUE=DATE:20200229", "SUMMARY:Y", "RRULE:FREQ=YEARLY"])
    assert [d for d, i in agenda(yearly, date(2024, 2, 28), 3).items() if i] == [date(2024, 2, 29)]


def test_cancelled_and_malformed_events():
    text = calendar(["DTSTART:20261116T090000", "SUMMARY:Gone", "STATUS:CANCELLED"],
                    ["DTSTART:garbage", "SUMMARY:Broken"], ["SUMMARY:No start"],
                    ["DTSTART:20261116T100000", "SUMMARY:Fine"])
    assert lines(agenda(text, date(2026, 11, 16)), date(2026, 11, 16)) == ["10:00        Fine"]


def test_cli_prints_headings_and_empty_days(tmp_path, capsys):
    f = tmp_path / "a.ics"
    f.write_text(calendar(["DTSTART:20261116T090000", "DTEND:20261116T100000", "SUMMARY:Plan"]))
    assert ia.main([str(f), "--date", "2026-11-16", "--days", "2"]) == 0
    out = capsys.readouterr().out
    assert "Monday 16 Nov 2026\n  09:00-10:00  Plan" in out
    assert "Tuesday 17 Nov 2026\n  Nothing scheduled." in out
    assert out.strip().endswith("1 item(s) over 2 day(s), times in UTC.")


def test_cli_errors(tmp_path, capsys):
    f = tmp_path / "a.ics"
    f.write_text("BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n")
    assert ia.main([str(f), "--date", "2026-11-16"]) == 1
    for args in (["--days", "0"], ["--tz", "Mars/Base"], ["--date", "soon"]):
        with pytest.raises(SystemExit):
            ia.main([str(f), *args])
    with pytest.raises(SystemExit):
        ia.main([str(tmp_path / "gone.ics")])
