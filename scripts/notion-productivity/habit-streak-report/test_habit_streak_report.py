import json
from datetime import date

import habit_streak_report as hsr
import pytest

TODAY = date(2026, 1, 8)
DATA = {"habits": {
    "read": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-05", "2026-01-06", "2026-01-07"],
    "exercise": ["2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05", "2026-01-06"],
    "meditate": ["2026-01-08", "2026-01-08", "2026-01-07"],
    "new": []}}


@pytest.fixture
def path(tmp_path):
    file = tmp_path / "h.json"
    file.write_text(json.dumps(DATA))
    return file


def days(*values):
    return [date.fromisoformat(v) for v in values]


def test_streaks_survive_until_the_end_of_today():
    run = days("2026-01-05", "2026-01-06", "2026-01-07")
    assert hsr.streaks(run, TODAY) == (3, 3)  # not done yet today, streak still alive
    assert hsr.streaks(run + days("2026-01-08"), TODAY) == (4, 4)
    assert hsr.streaks(days("2026-01-04", "2026-01-05"), TODAY) == (0, 2)  # broken
    assert hsr.streaks([], TODAY) == (0, 0)
    assert hsr.streaks(days("2026-01-07", "2026-01-09", "2026-01-10"), TODAY) == (1, 1)


def test_load_dedupes_and_sorts(path):
    habits = hsr.load(path)
    assert habits["meditate"] == days("2026-01-07", "2026-01-08") and habits["new"] == []


def test_report_for_read_is_at_risk():
    item = hsr.report_for("read", days(*DATA["habits"]["read"]), TODAY, 7)
    assert (item["current"], item["best"], item["total"]) == (3, 3, 6)
    assert item["window_done"] == 5 and item["consistency"] == 71  # Jan 2-8 holds 5 of 7 days
    assert item["at_risk"] and item["days_since"] == 1
    assert item["recent"].endswith("##-") and len(item["recent"]) == 14


def test_flags():
    risky = {"at_risk": True, "current": 3, "days_since": 1, "last_done": "x"}
    assert hsr.flags(risky) == "do it today to keep the streak"
    assert hsr.flags({"at_risk": False, "current": 0, "days_since": 2, "last_done": "x"}) == (
        "broken 2 day(s) ago")
    assert hsr.flags({"at_risk": False, "current": 0, "days_since": None, "last_done": None}) == (
        "never done")
    assert hsr.flags({"at_risk": False, "current": 2, "days_since": 0, "last_done": "x"}) == (
        "done today")


def test_cli_text_markdown_json(path, capsys):
    assert hsr.main([str(path), "--today", "2026-01-08", "--window", "7"]) == 0
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert lines[0] == "Habit streaks as of 2026-01-08"
    assert lines[3].startswith("read") and lines[4].startswith("meditate")  # longest streak first
    assert "do it today" in out and "broken 2 day(s) ago" in out and "never done" in out
    assert "Longest running streak: read (3 day(s))." in out
    assert "Overall: 12 check-ins of 28 possible (43%)" in out
    assert hsr.main([str(path), "--today", "2026-01-08", "--format", "markdown",
                     "--habit", "read"]) == 0
    assert "| read | 3 | 3 |" in capsys.readouterr().out
    assert hsr.main([str(path), "--today", "2026-01-08", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["window"] == 30 and [h["habit"] for h in data["habits"]][0] == "read"


def test_cli_errors(path, tmp_path, capsys):
    assert hsr.main([str(path), "--habit", "swim"]) == 1
    assert "No such habit: swim" in capsys.readouterr().err
    assert hsr.main([str(tmp_path / "missing.json")]) == 1
    bad = tmp_path / "bad.json"
    bad.write_text('{"habits": {"x": ["2026-13-45"]}}')
    assert hsr.main([str(bad)]) == 1
    bad.write_text('{"habits": []}')
    assert hsr.main([str(bad)]) == 1
    bad.write_text('{"habits": {}}')
    assert hsr.main([str(bad)]) == 1
    for argv in (["--window", "0"], ["--today", "tomorrow"]):
        with pytest.raises(SystemExit):
            hsr.main([str(path), *argv])
