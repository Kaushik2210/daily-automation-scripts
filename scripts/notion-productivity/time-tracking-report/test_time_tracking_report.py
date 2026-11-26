import json
from datetime import date

import pytest
import time_tracking_report as ttr

LOG = """date,start,end,project,task
2026-11-09,09:00,10:30,web,design
2026-11-09,11:00,12:00,app,api
2026-11-10,22:00,00:30,web,build
2026-11-16,09:00,09:10,app,api
bad-date,09:00,10:00,web,x
2026-11-17,10:00,09:00,web,zero
"""


@pytest.fixture
def log(tmp_path):
    path = tmp_path / "log.csv"
    path.write_text(LOG, encoding="utf-8")
    return path


def test_entry_minutes_from_hours_and_clock_times():
    assert ttr.entry_minutes({"hours": "1.5"}) == 90
    assert ttr.entry_minutes({"start": "09:00", "end": "10:30"}) == 90
    assert ttr.entry_minutes({"start": "22:00", "end": "00:30"}) == 150  # past midnight
    with pytest.raises(ValueError):
        ttr.entry_minutes({"hours": "0"})
    with pytest.raises(ValueError):
        ttr.entry_minutes({"start": "9am", "end": "10:00"})
    with pytest.raises(ValueError, match="23.0 hours"):  # end before start is not a night shift
        ttr.entry_minutes({"start": "10:00", "end": "09:00"})
    with pytest.raises(ValueError):
        ttr.entry_minutes({"hours": "20"})


def test_read_log_collects_problems_and_rounds_up(log):
    entries, problems = ttr.read_log(log, 0)
    assert len(entries) == 4 and len(problems) == 2
    assert problems[0].startswith("line 6") and "line 7" in problems[1]
    rounded, _ = ttr.read_log(log, 15)
    assert [e["minutes"] for e in rounded] == [90, 60, 150, 15]


def test_read_log_requires_the_right_columns(tmp_path):
    path = tmp_path / "x.csv"
    path.write_text("when,what\n1,2\n")
    with pytest.raises(ValueError):
        ttr.read_log(path, 0)
    path.write_text("date,project,hours\n2026-11-09,web,2\n")
    assert ttr.read_log(path, 0)[0][0]["minutes"] == 120


def test_parse_rates():
    assert ttr.parse_rates(["50", "web=80"]) == (50.0, {"web": 80.0})
    assert ttr.parse_rates([]) == (None, {})
    with pytest.raises(ValueError):
        ttr.parse_rates(["fast"])


def test_grouping_and_billing(log):
    entries, _ = ttr.read_log(log, 0)
    rows = dict(ttr.summarise(entries, "project", 50.0, {"web": 100.0}))
    assert rows["web"]["minutes"] == 240 and rows["web"]["amount"] == pytest.approx(400)
    assert rows["app"]["minutes"] == 70 and rows["app"]["amount"] == pytest.approx(70 / 60 * 50)
    assert [k for k, _ in ttr.summarise(entries, "week", None, {})] == ["2026-W46", "2026-W47"]
    assert [k for k, _ in ttr.summarise(entries, "day", None, {})][0] == "2026-11-09"
    assert "web / design" in dict(ttr.summarise(entries, "task", None, {}))
    untitled = {"date": date(2026, 1, 1), "project": "p", "task": ""}
    assert ttr.key_for(untitled, "task") == "p / (no task)"


def test_cli_text_markdown_json_csv(log, capsys):
    assert ttr.main([str(log), "--rate", "web=100"]) == 0
    out = capsys.readouterr()
    assert "web" in out.out and "4.00" in out.out and "Total" in out.out and "amount" in out.out
    assert "3 day(s)" in out.out and "Skipped line 6" in out.err
    assert ttr.main([str(log), "--format", "markdown"]) == 0
    assert "| **Total** | 5.17 | 100% |" in capsys.readouterr().out
    assert ttr.main([str(log), "--format", "json", "--group-by", "day", "--rate", "60"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["total_hours"] == 5.17 and data["groups"][0]["amount"] == 150.0
    assert ttr.main([str(log), "--format", "csv", "--project", "app"]) == 0
    assert capsys.readouterr().out.splitlines()[1] == '"app",1.17,100.0'


def test_cli_filters_and_errors(log, tmp_path, capsys):
    window = ["--from", "2026-11-10", "--to", "2026-11-16", "--format", "csv"]
    assert ttr.main([str(log), *window]) == 0
    assert capsys.readouterr().out.count("\n") == 3  # header + 2 projects
    assert ttr.main([str(log), "--project", "nope"]) == 1
    assert "No time entries match" in capsys.readouterr().err
    assert ttr.main([str(tmp_path / "missing.csv")]) == 1
    with pytest.raises(SystemExit):
        ttr.main([str(log), "--from", "yesterday"])
    with pytest.raises(SystemExit):
        ttr.main([str(log), "--round", "-5"])
