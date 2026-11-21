import csv
import platform

import active_window_logger as awl
import pytest


def feed(windows):
    items = iter(windows)
    last = [windows[-1]]

    def reader():
        last[0] = next(items, last[0])
        return last[0]
    return reader


def run_watch(windows, log, **kwargs):
    lines = []
    defaults = {"interval": 0, "seconds": 0, "count": 0, "titles": True}
    defaults.update(kwargs)
    ticks = iter(range(1000))
    written = awl.watch(feed(windows), log, sleep=lambda s: None, clock=lambda: next(ticks),
                        out=lines.append, **defaults)
    return written, lines


def test_logs_only_changes(tmp_path):
    log = tmp_path / "w.csv"
    windows = [("code", "main.py"), ("code", "main.py"), ("chrome", "Docs"), ("chrome", "Docs"),
               ("code", "main.py")]
    written, lines = run_watch(windows, log, count=3)
    assert written == 3 and len(lines) == 3
    rows = awl.read_log(log)
    assert [(r["app"], r["title"]) for r in rows] == [
        ("code", "main.py"), ("chrome", "Docs"), ("code", "main.py")]
    assert list(csv.reader(log.open(encoding="utf-8")))[0] == awl.FIELDS


def test_title_change_in_the_same_app_is_a_change(tmp_path):
    written, _ = run_watch([("code", "a.py"), ("code", "b.py")], tmp_path / "w.csv", count=2)
    assert written == 2


def test_no_titles_mode_hides_titles_and_merges_same_app(tmp_path):
    log = tmp_path / "w.csv"
    written, _ = run_watch([("code", "secret.py"), ("code", "other.py"), ("chrome", "Bank")], log,
                           count=2, titles=False)
    assert written == 2
    assert [(r["app"], r["title"]) for r in awl.read_log(log)] == [("code", ""), ("chrome", "")]


def test_empty_windows_are_ignored_and_time_limit_stops(tmp_path):
    written, _ = run_watch([("", ""), ("app", "t")] * 50, tmp_path / "w.csv", seconds=6)
    assert 0 < written <= 6


def test_appending_does_not_repeat_the_header(tmp_path):
    log = tmp_path / "w.csv"
    awl.append(log, {"time": "2026-11-21T09:00:00", "app": "a", "title": "t"})
    awl.append(log, {"time": "2026-11-21T09:01:00", "app": "b", "title": "u"})
    assert log.read_text(encoding="utf-8").count("time,app,title") == 1


def test_show_and_missing_log(tmp_path, capsys):
    log = tmp_path / "w.csv"
    for minute in range(4):
        awl.append(log, {"time": f"2026-11-21T09:0{minute}:00", "app": f"app{minute}",
                         "title": f"title {minute}"})
    assert awl.main(["show", "--log", str(log), "--last", "2"]) == 0
    out = capsys.readouterr().out
    assert "app3" in out and "app1" not in out and "Showing 2 of 4" in out
    assert awl.main(["show", "--log", str(tmp_path / "none.csv")]) == 1


def test_watch_reports_an_unsupported_system(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(awl, "active_window", lambda: (_ for _ in ()).throw(OSError("no X11")))
    assert awl.main(["watch", "--log", str(tmp_path / "w.csv"), "--count", "1"]) == 1
    assert "Can't read the active window: no X11" in capsys.readouterr().err


@pytest.mark.skipif(platform.system() != "Windows", reason="uses the Windows API")
def test_real_windows_call_returns_strings():
    app, title = awl.windows_active_window()
    assert isinstance(app, str) and isinstance(title, str)
