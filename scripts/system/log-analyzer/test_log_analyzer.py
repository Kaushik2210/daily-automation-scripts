from datetime import datetime

import log_analyzer as la
import pytest

LOG = """2026-11-10 08:00:01,123 INFO     [api] started
2026-11-10 08:30:00 WARN [db] slow query (812 ms)
2026-11-10 09:01:00,001 ERROR    [db] connection refused to 10.0.0.5
Traceback (most recent call last):
  File "x.py", line 3, in run
RuntimeError: connection refused
2026-11-10 09:02:00 ERROR [db] connection refused to 10.0.0.9
2026-11-10 09:03:00 error [api] payment timeout after 30 s
2026-11-10T09:04:00Z FATAL out of memory
2026-11-10 09:05:00 just a line without a level
"""


def test_parse_time_formats():
    assert la.parse_time("2026-11-10 09:15:02,123 INFO x", 2000) == datetime(2026, 11, 10, 9, 15, 2)
    assert la.parse_time("2026-11-10T09:15:02Z x", 2000) == datetime(2026, 11, 10, 9, 15, 2)
    assert la.parse_time('1.2.3.4 - - [10/Nov/2026:09:15:02 +0000] "GET /"', 2000) == (
        datetime(2026, 11, 10, 9, 15, 2))
    assert la.parse_time("Nov  3 04:05:06 host sshd[1]: hi", 2025) == datetime(2025, 11, 3, 4, 5, 6)
    assert la.parse_time("no time here", 2026) is None
    assert la.parse_time("2026-13-45 99:99:99 x", 2026) is None


@pytest.mark.parametrize("line,level", [
    ("x WARN y", "WARNING"), ("x warning y", "WARNING"), ("x ERR y", "ERROR"),
    ("x FATAL y", "CRITICAL"), ("x severe y", "CRITICAL"), ("x Debug y", "DEBUG"),
    ("nothing here", None), ("informative text", None)])
def test_parse_level(line, level):
    assert la.parse_level(line) == level


def test_entries_group_continuation_lines_and_count_strays():
    entries, orphans = la.parse_entries(["stray first line", *LOG.splitlines()], 2026)
    assert orphans == 1 and len(entries) == 7
    assert entries[2]["extra"] == 3  # the traceback belongs to the first ERROR
    assert [e["level"] for e in entries] == [
        "INFO", "WARNING", "ERROR", "ERROR", "ERROR", "CRITICAL", None]


def test_normalise_groups_repeats_of_the_same_problem():
    a = la.normalise("2026-11-10 09:01:00,001 ERROR    [db] connection refused to 10.0.0.5")
    b = la.normalise("2026-11-10 09:02:00 ERROR [db] connection refused to 10.0.0.9")
    assert a == b == "connection refused to #.#.#.#"
    assert la.normalise("2026-11-10 09:03:00 error [api] payment timeout after 30 s") == (
        "payment timeout after # s")


def test_summarize_counts_levels_hours_and_errors():
    entries, _ = la.parse_entries(LOG.splitlines(), 2026)
    levels, hours, errors = la.summarize(entries)
    assert levels["ERROR"] == 3 and levels["(none)"] == 1 and levels["CRITICAL"] == 1
    assert hours[datetime(2026, 11, 10, 9)] == 5 and hours[datetime(2026, 11, 10, 8)] == 2
    assert errors.most_common(1) == [("connection refused to #.#.#.#", 2)]


def test_report_text(tmp_path, capsys):
    path = tmp_path / "app.log"
    path.write_text(LOG)
    assert la.main([str(path), "--top", "2"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("7 entries from 2026-11-10 08:00:01 to 2026-11-10 09:05:00")
    assert "3 continuation line(s)" in out
    assert "ERROR" in out and "42.9%" in out
    assert "2026-11-10 09:00" in out and "Busiest hours (top 2)" in out
    assert "2x  connection refused to #.#.#.#" in out


def test_clean_log_has_no_errors(tmp_path, capsys):
    path = tmp_path / "ok.log"
    path.write_text("2026-11-10 08:00:00 INFO fine\n2026-11-10 08:01:00 INFO fine\n")
    assert la.main([str(path)]) == 0
    assert "No ERROR or CRITICAL entries." in capsys.readouterr().out


def test_several_files_and_bad_input(tmp_path, capsys):
    one, two = tmp_path / "a.log", tmp_path / "b.log"
    one.write_text("2026-11-10 08:00:00 INFO a\n")
    two.write_text("2026-11-10 09:00:00 ERROR b\n")
    assert la.main([str(one), str(two)]) == 0
    assert capsys.readouterr().out.startswith("2 entries")
    empty = tmp_path / "empty.log"
    empty.write_text("nothing with a date\n")
    assert la.main([str(empty)]) == 1
    assert la.main([str(tmp_path / "gone.log")]) == 1
    with pytest.raises(SystemExit):
        la.main([str(one), "--top", "0"])
