import re
from datetime import datetime, timedelta

import log_timeline as lt
import pytest

LOG = """2026-11-10 08:05:00 INFO a
2026-11-10 08:40:00 ERROR b
2026-11-10 08:41:00 ERROR c
2026-11-10 10:10:00 WARN d
Traceback line without a time
2026-11-10 10:59:59 INFO e
2026-11-10 10:30:00 INFO payment ok
"""


def test_parse_bucket():
    assert lt.parse_bucket("30s") == timedelta(seconds=30)
    assert lt.parse_bucket("10m") == timedelta(minutes=10)
    assert lt.parse_bucket("2H") == timedelta(hours=2)
    assert lt.parse_bucket("1d") == timedelta(days=1)
    for bad in ("", "hour", "0m", "10", "5x"):
        with pytest.raises(Exception, match="bucket"):
            lt.parse_bucket(bad)


@pytest.mark.parametrize("when,size,expected", [
    (datetime(2026, 11, 10, 9, 47, 12), timedelta(hours=1), datetime(2026, 11, 10, 9, 0)),
    (datetime(2026, 11, 10, 9, 47, 12), timedelta(minutes=10), datetime(2026, 11, 10, 9, 40)),
    (datetime(2026, 11, 10, 9, 47, 12), timedelta(seconds=30), datetime(2026, 11, 10, 9, 47, 0)),
    (datetime(2026, 11, 10, 23, 59, 59), timedelta(days=1), datetime(2026, 11, 10, 0, 0)),
    (datetime(2026, 11, 10, 9, 47, 12), timedelta(hours=7), datetime(2026, 11, 10, 7, 0))])
def test_floor_time(when, size, expected):
    assert lt.floor_time(when, size) == expected


def test_collect_counts_buckets_levels_and_skipped_lines():
    counts, levels, skipped = lt.collect(LOG.splitlines(), 2026, timedelta(hours=1))
    assert counts == {datetime(2026, 11, 10, 8): 3, datetime(2026, 11, 10, 10): 3}
    assert levels[datetime(2026, 11, 10, 8)] == {"INFO": 1, "ERROR": 2} and skipped == 1


def test_collect_filters_by_level_and_pattern():
    counts, _, _ = lt.collect(LOG.splitlines(), 2026, timedelta(hours=1), level="ERROR")
    assert counts == {datetime(2026, 11, 10, 8): 2}
    counts, _, _ = lt.collect(LOG.splitlines(), 2026, timedelta(hours=1), level="WARNING")
    assert counts == {datetime(2026, 11, 10, 10): 1}  # WARN is the same level as WARNING
    counts, _, _ = lt.collect(LOG.splitlines(), 2026, timedelta(hours=1),
                              pattern=re.compile("payment"))
    assert counts == {datetime(2026, 11, 10, 10): 1}


def test_render_fills_gaps_and_marks_the_peak():
    counts, levels, _ = lt.collect(LOG.splitlines(), 2026, timedelta(hours=1))
    rows = lt.render(counts, levels, timedelta(hours=1), 10, fill=True)
    assert [r.split()[1] for r in rows] == ["08:00", "09:00", "10:00"]
    assert rows[0].endswith("<-- peak") and "E2 I1" in rows[0]
    assert rows[1].split()[2] == "0" and "#" not in rows[1]
    assert len(lt.render(counts, levels, timedelta(hours=1), 10, fill=False)) == 2


def test_daily_buckets_show_dates_only_and_too_many_rows_are_refused():
    lines = ["2026-11-10 08:00:00 INFO a", "2026-11-12 09:00:00 INFO b"]
    counts, levels, _ = lt.collect(lines, 2026, timedelta(days=1))
    rows = lt.render(counts, levels, timedelta(days=1), 10, fill=True)
    assert [r.split()[0] for r in rows] == ["2026-11-10", "2026-11-11", "2026-11-12"]
    wide = ["2020-01-01 00:00:00 INFO a", "2026-01-01 00:00:00 INFO b"]
    counts, levels, _ = lt.collect(wide, 2026, timedelta(minutes=1))
    with pytest.raises(ValueError, match="bigger --bucket"):
        lt.render(counts, levels, timedelta(minutes=1), 10, fill=True)


def test_cli_prints_a_timeline(tmp_path, capsys):
    path = tmp_path / "app.log"
    path.write_text(LOG)
    assert lt.main([str(path), "--bucket", "1h", "--width", "10"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("6 event(s) in 2 bucket(s) of 1:00:00 (1 line(s) without a timestamp")
    assert "2026-11-10 09:00      0" in out and "Letters show levels" in out
    assert lt.main([str(path), "--no-fill", "--level", "ERROR"]) == 0
    assert "09:00" not in capsys.readouterr().out


def test_no_events_and_bad_arguments(tmp_path, capsys):
    path = tmp_path / "app.log"
    path.write_text(LOG)
    assert lt.main([str(path), "--pattern", "nothing-matches"]) == 1
    assert lt.main([str(tmp_path / "gone.log")]) == 1
    for args in (["--width", "2"], ["--pattern", "("], ["--bucket", "soon"], ["--level", "LOUD"]):
        with pytest.raises(SystemExit):
            lt.main([str(path), *args])
