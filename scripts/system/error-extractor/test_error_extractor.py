import re

import error_extractor as ee
import pytest

LINES = [
    "2026-11-10 09:00:00 INFO start",                         # 0
    "2026-11-10 09:00:01 INFO working",                       # 1
    "2026-11-10 09:00:02 ERROR [db] connection refused",      # 2
    "Traceback (most recent call last):",                     # 3
    '  File "x.py", line 3, in run',                          # 4
    "RuntimeError: connection refused",                       # 5
    "2026-11-10 09:00:03 INFO retrying",                      # 6
    "2026-11-10 09:00:04 INFO fine",                          # 7
    "2026-11-10 09:00:05 INFO fine again",                    # 8
    "2026-11-10 09:00:06 INFO still fine",                    # 9
    "2026-11-10 09:00:07 FATAL out of memory",                # 10
    "2026-11-10 09:00:08 WARN just a warning",                # 11
]
LEVELS = {"ERROR", "CRITICAL"}


def test_starts_entry_and_level_of():
    assert ee.starts_entry("2026-11-10 09:00:00 x") and ee.starts_entry("Nov  3 04:05:06 host x")
    assert ee.starts_entry('1.2.3.4 - [10/Nov/2026:09:00:00 +0000]') is False  # IP comes first
    assert ee.starts_entry("[10/Nov/2026:09:00:00 +0000] x")
    assert not ee.starts_entry("  File x.py")
    levels = [ee.level_of(x) for x in ("a FATAL b", "a err b", "plain")]
    assert levels == ["CRITICAL", "ERROR", None]


def test_blocks_include_the_stack_trace_and_leading_context():
    blocks = ee.find_blocks(LINES, LEVELS, None, before=1, after=0)
    assert blocks == [(1, 5, {2}), (9, 10, {10})]


def test_after_adds_lines_and_overlapping_blocks_merge():
    apart = ee.find_blocks(LINES, LEVELS, None, before=2, after=1)
    assert apart == [(0, 6, {2}), (8, 11, {10})]
    merged = ee.find_blocks(LINES, LEVELS, None, before=2, after=3)
    assert merged == [(0, 11, {2, 10})]


def test_pattern_overrides_levels_and_levels_need_a_timestamped_line():
    blocks = ee.find_blocks(LINES, LEVELS, re.compile("fine"), before=0, after=0)
    assert blocks == [(7, 9, {7, 8, 9})]
    noisy = ["    ERROR inside a stack trace", "2026-11-10 09:00:00 INFO ok"]
    assert ee.find_blocks(noisy, LEVELS, None, 0, 0) == []


def test_format_marks_matches_and_separates_blocks():
    blocks = ee.find_blocks(LINES, LEVELS, None, before=0, after=0)
    text = ee.format_blocks("app.log", LINES, blocks, show_name=False)
    assert text[0] == ">  3  2026-11-10 09:00:02 ERROR [db] connection refused"
    assert text[1].startswith("   4  Traceback") and "--" in text
    assert ee.format_blocks("app.log", LINES, blocks[:1], True)[0].startswith("> app.log: 3")


def write_log(tmp_path):
    path = tmp_path / "app.log"
    path.write_text("\n".join(LINES) + "\n")
    return path


def test_cli_prints_blocks_and_summary(tmp_path, capsys):
    assert ee.main([str(write_log(tmp_path)), "--before", "1"]) == 0
    out = capsys.readouterr().out
    assert "> " in out and "RuntimeError: connection refused" in out
    assert "out of memory" in out and "just a warning" not in out
    assert out.strip().endswith("2 matching entries found.")


def test_levels_pattern_count_and_exit_codes(tmp_path, capsys):
    path = write_log(tmp_path)
    assert ee.main([str(path), "--levels", "warn", "--count"]) == 0
    assert capsys.readouterr().out.strip() == "1 matching entry found."
    assert ee.main([str(path), "--pattern", "OUT OF", "-i", "--count"]) == 0
    assert ee.main([str(path), "--pattern", "nomatch", "--count"]) == 1
    assert ee.main([str(path), "--levels", "TRACE"]) == 1


def test_several_files_get_headers_and_out_is_never_overwritten(tmp_path, capsys):
    one = write_log(tmp_path)
    two = tmp_path / "other.log"
    two.write_text("2026-11-10 10:00:00 ERROR elsewhere\n")
    out = tmp_path / "errors.txt"
    assert ee.main([str(one), str(two), "--out", str(out)]) == 0
    saved = out.read_text()
    assert "==== " in saved and "other.log:" in saved and "elsewhere" in saved
    assert "3 matching entries found. Saved to" in capsys.readouterr().out
    assert ee.main([str(one), "--out", str(out)]) == 1 and out.read_text() == saved


def test_bad_arguments(tmp_path, capsys):
    path = write_log(tmp_path)
    for args in (["--before", "-1"], ["--pattern", "("]):
        with pytest.raises(SystemExit):
            ee.main([str(path), *args])
    assert ee.main([str(tmp_path / "gone.log")]) == 1
