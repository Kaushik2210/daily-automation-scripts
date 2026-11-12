from datetime import datetime

import log_merger as lm
import pytest

A = """2026-11-10 09:00:00 INFO a1
2026-11-10 09:02:00 ERROR a2
Traceback (most recent call last):
  File "a.py", line 1
2026-11-10 09:04:00 INFO a3
"""
B = """2026-11-10 09:01:00 INFO b1
2026-11-10 09:02:00 INFO b2 same second as a2
2026-11-10 09:05:00 INFO b3
"""


def test_read_entries_groups_continuations_and_keeps_stray_lines(tmp_path):
    path = tmp_path / "a.log"
    path.write_text("junk before any time\n" + A)
    entries = lm.read_entries(path, 2026)
    assert [len(lines) for _, lines in entries] == [1, 1, 3, 1]
    assert entries[0] == (datetime(2026, 11, 10, 9, 0), ["junk before any time"])
    assert entries[2][1][1] == "Traceback (most recent call last):"


def test_merge_interleaves_by_time_and_keeps_traces_with_their_entry(tmp_path):
    (tmp_path / "a.log").write_text(A)
    (tmp_path / "b.log").write_text(B)
    sources = [("a", lm.read_entries(tmp_path / "a.log", 2026)),
               ("b", lm.read_entries(tmp_path / "b.log", 2026))]
    merged, disordered = lm.merge(sources)
    assert merged == [
        "2026-11-10 09:00:00 INFO a1",
        "2026-11-10 09:01:00 INFO b1",
        "2026-11-10 09:02:00 ERROR a2",
        "Traceback (most recent call last):",
        '  File "a.py", line 1',
        "2026-11-10 09:02:00 INFO b2 same second as a2",
        "2026-11-10 09:04:00 INFO a3",
        "2026-11-10 09:05:00 INFO b3"]
    assert disordered == 0


def test_ties_keep_file_order_and_labels_are_added(tmp_path):
    (tmp_path / "a.log").write_text("2026-11-10 09:02:00 INFO from a\n")
    (tmp_path / "b.log").write_text("2026-11-10 09:02:00 INFO from b\n")
    sources = [("a", lm.read_entries(tmp_path / "a.log", 2026)),
               ("b", lm.read_entries(tmp_path / "b.log", 2026))]
    merged, _ = lm.merge(sources, label=True)
    assert merged == ["[a] 2026-11-10 09:02:00 INFO from a", "[b] 2026-11-10 09:02:00 INFO from b"]


def test_out_of_order_entries_inside_one_file_are_sorted_and_counted(tmp_path):
    (tmp_path / "a.log").write_text(
        "2026-11-10 09:05:00 INFO late\n2026-11-10 09:01:00 INFO early\n")
    merged, disordered = lm.merge([("a", lm.read_entries(tmp_path / "a.log", 2026))])
    assert disordered == 1 and merged[0].endswith("early")


def test_cli_prints_merged_log_and_summary_on_stderr(tmp_path, capsys):
    (tmp_path / "a.log").write_text(A)
    (tmp_path / "b.log").write_text(B)
    assert lm.main([str(tmp_path / "a.log"), str(tmp_path / "b.log"), "--label"]) == 0
    captured = capsys.readouterr()
    assert captured.out.splitlines()[0] == "[a] 2026-11-10 09:00:00 INFO a1"
    assert "[b] 2026-11-10 09:01:00 INFO b1" in captured.out
    assert "Merged 6 entries from 2 file(s)." in captured.err


def test_since_until_filter_and_out_file(tmp_path, capsys):
    (tmp_path / "a.log").write_text(A)
    (tmp_path / "b.log").write_text(B)
    out = tmp_path / "all.log"
    args = [str(tmp_path / "a.log"), str(tmp_path / "b.log"), "--since", "2026-11-10 09:02",
            "--until", "2026-11-10 09:04", "--out", str(out)]
    assert lm.main(args) == 0
    text = out.read_text()
    assert "a1" not in text and "b3" not in text and "a3" in text and "same second" in text
    assert "Saved to" in capsys.readouterr().out
    assert lm.main(args) == 1  # the output file already exists


def test_syslog_dates_use_the_given_year(tmp_path, capsys):
    (tmp_path / "s.log").write_text("Nov 10 09:00:01 host app: hello\n")
    (tmp_path / "t.log").write_text("Nov 10 08:59:59 host app: earlier\n")
    assert lm.main([str(tmp_path / "s.log"), str(tmp_path / "t.log"), "--year", "2026"]) == 0
    assert capsys.readouterr().out.splitlines()[0].endswith("earlier")


def test_errors(tmp_path, capsys):
    path = tmp_path / "a.log"
    path.write_text("")
    assert lm.main([str(path)]) == 1
    assert lm.main([str(tmp_path / "gone.log")]) == 1
    with pytest.raises(SystemExit):
        lm.main([str(path), "--since", "yesterday"])
