import re
import threading
import time

import log_tail_filter as ltf
import pytest

LOG = """2026-11-10 09:00:00 INFO start
2026-11-10 09:00:01 DEBUG cache miss
2026-11-10 09:00:02 WARNING slow query
2026-11-10 09:00:03 ERROR database down
2026-11-10 09:00:04 INFO payment ok
2026-11-10 09:00:05 ERROR payment failed
"""


def test_filter_pattern_exclude_and_level():
    f = ltf.LineFilter(re.compile("payment"), [re.compile("ok")])
    assert [f.accepts(x) for x in ("payment failed", "payment ok", "other")] == [True, False, False]
    warn = ltf.LineFilter(min_level="WARNING")
    assert [warn.accepts(x) for x in ("a INFO b", "a WARN b", "a ERROR b", "no level")] == [
        False, True, True, False]
    assert ltf.LineFilter().accepts("anything at all")


def test_last_lines_reads_from_the_end(tmp_path):
    path = tmp_path / "a.log"
    path.write_text("".join(f"line {i}\n" for i in range(1000)))
    assert ltf.last_lines(path, 3) == ["line 997", "line 998", "line 999"]
    assert len(ltf.last_lines(path, 5000)) == 1000
    assert ltf.last_lines(path, 0) == []
    short = tmp_path / "short.log"
    short.write_text("only\nfew")
    assert ltf.last_lines(short, 10) == ["only", "few"]


def test_no_follow_shows_the_last_matching_lines(tmp_path, capsys):
    path = tmp_path / "app.log"
    path.write_text(LOG)
    assert ltf.main([str(path), "--no-follow", "-p", "ERROR|payment", "-n", "2"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "2026-11-10 09:00:04 INFO payment ok", "2026-11-10 09:00:05 ERROR payment failed"]
    assert ltf.main([str(path), "--no-follow", "--level", "ERROR", "-x", "database"]) == 0
    assert capsys.readouterr().out.strip().endswith("payment failed")
    assert ltf.main([str(path), "--no-follow", "-p", "nomatch"]) == 1
    assert ltf.main([str(path), "--no-follow", "-p", "PAYMENT", "-i", "-n", "1"]) == 0


def test_follow_prints_new_matching_lines_only(tmp_path):
    path = tmp_path / "live.log"
    path.write_text("2026-11-10 09:00:00 INFO old line\n")
    seen = []

    def writer():
        time.sleep(0.2)
        with path.open("a") as handle:
            handle.write("2026-11-10 09:01:00 INFO ignored\n")
            handle.write("2026-11-10 09:01:01 ERROR first problem\n")
            handle.write("2026-11-10 09:01:02 ERR")  # a half-written line
            handle.flush()
            time.sleep(0.2)
            handle.write("OR second problem\n")

    thread = threading.Thread(target=writer)
    thread.start()
    count = ltf.follow(path, ltf.LineFilter(re.compile("ERROR")), seen.append, interval=0.05,
                       max_seconds=2.0, max_matches=2)
    thread.join()
    assert count == 2
    assert seen == ["2026-11-10 09:01:01 ERROR first problem",
                    "2026-11-10 09:01:02 ERROR second problem"]


def test_follow_survives_rotation(tmp_path):
    path = tmp_path / "rot.log"
    path.write_text("2026-11-10 09:00:00 INFO a long first line that will be rotated away\n")
    seen = []

    def rotate():
        time.sleep(0.2)
        path.write_text("2026-11-10 09:05:00 ERROR after rotation\n")  # a shorter, new file

    thread = threading.Thread(target=rotate)
    thread.start()
    ltf.follow(path, ltf.LineFilter(), seen.append, interval=0.05, max_seconds=1.5, max_matches=1)
    thread.join()
    assert seen == ["2026-11-10 09:05:00 ERROR after rotation"]


def test_follow_stops_after_max_seconds_with_a_fake_clock(tmp_path):
    path = tmp_path / "quiet.log"
    path.write_text("x\n")
    ticks = iter(range(0, 100))
    sleeps = []
    result = ltf.follow(path, ltf.LineFilter(), print, interval=1.0, max_seconds=3,
                        clock=lambda: next(ticks), sleep=sleeps.append)
    assert result == 0 and len(sleeps) >= 2


def test_cli_follow_with_a_time_limit(tmp_path, capsys):
    path = tmp_path / "app.log"
    path.write_text(LOG)
    assert ltf.main([str(path), "-p", "ERROR", "-n", "1", "--max-seconds", "0.2",
                     "--interval", "0.05"]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip().endswith("payment failed") and "following" in captured.err


def test_bad_arguments(tmp_path):
    path = tmp_path / "a.log"
    path.write_text("x\n")
    for args in ([str(tmp_path / "gone")], [str(path), "-p", "("], [str(path), "-n", "-1"]):
        with pytest.raises(SystemExit):
            ltf.main(args)
