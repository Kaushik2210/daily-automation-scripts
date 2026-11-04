from datetime import date

import pytest
from habit_tracker import grid, load, main, streaks

TODAY = date(2026, 1, 7)


def test_streaks_current_and_best():
    dates = ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-05", "2026-01-06", "2026-01-07"]
    assert streaks(dates, TODAY) == (3, 3)
    assert streaks(["2026-01-01", "2026-01-02"], TODAY) == (0, 2)
    assert streaks([], TODAY) == (0, 0)


def test_yesterday_keeps_streak_alive():
    assert streaks(["2026-01-05", "2026-01-06"], TODAY) == (2, 2)


def test_grid_shows_recent_history():
    assert grid(["2026-01-07", "2026-01-05"], TODAY, length=5) == "..#.#"


def test_check_uncheck_and_report(tmp_path, capsys):
    f = str(tmp_path / "h.json")
    main(["check", "read", "--file", f, "--today", "2026-01-07"])
    main(["check", "read", "--date", "2026-01-06", "--file", f, "--today", "2026-01-07"])
    assert "Current streak: 2" in capsys.readouterr().out
    main(["report", "--file", f, "--today", "2026-01-07"])
    out = capsys.readouterr().out
    assert "read" in out and out.splitlines()[-1].endswith("............##")
    main(["uncheck", "read", "--file", f, "--today", "2026-01-07"])
    assert load(tmp_path / "h.json")["habits"]["read"] == ["2026-01-06"]


def test_check_needs_name_and_bad_date(tmp_path):
    with pytest.raises(SystemExit):
        main(["check", "--file", str(tmp_path / "h.json")])
    with pytest.raises(SystemExit):
        main(["list", "--today", "31-01-2026", "--file", str(tmp_path / "h.json")])
