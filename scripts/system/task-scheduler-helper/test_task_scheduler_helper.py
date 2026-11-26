import xml.etree.ElementTree as ET

import pytest
import task_scheduler_helper as tsh


def sched(every, at=None, days=None, dom=1):
    return tsh.parse_schedule(every, at, days, dom)


@pytest.mark.parametrize("args,kind,n", [
    (("15m", None, None, 1), "minutes", 15), (("2h", None, None, 1), "hours", 2),
    (("hourly", None, None, 1), "hours", 1), (("DAILY", "08:30", None, 1), "daily", 1),
    (("weekly", None, "Wed, mon", 1), "weekly", 1), (("monthly", None, None, 5), "monthly", 1)])
def test_parse_schedule(args, kind, n):
    result = tsh.parse_schedule(*args)
    assert result["kind"] == kind and result["n"] == n


def test_parse_schedule_details():
    weekly = sched("weekly", "07:05", "wed,mon,wed")
    assert (weekly["hour"], weekly["minute"], weekly["days"]) == (7, 5, [0, 2])
    assert sched("weekly")["days"] == [0]  # defaults to Monday
    assert sched("daily")["hour"] == 9 and sched("monthly", dom=28)["dom"] == 28


@pytest.mark.parametrize("args", [("0m", None, None, 1), ("90m", None, None, 1),
                                  ("24h", None, None, 1), ("soon", None, None, 1),
                                  ("daily", "25:00", None, 1), ("daily", "8am", None, 1),
                                  ("weekly", None, "funday", 1), ("monthly", None, None, 31)])
def test_bad_schedules_are_rejected(args):
    with pytest.raises(ValueError):
        tsh.parse_schedule(*args)


def test_explain():
    assert tsh.explain(sched("15m")) == "every 15 minute(s)"
    assert tsh.explain(sched("weekly", "02:30", "mon,fri")) == "every Mon, Fri at 02:30"
    assert tsh.explain(sched("monthly", "06:00", dom=15)) == "on day 15 of every month at 06:00"


@pytest.mark.parametrize("every,at,days,dom,expected", [
    ("15m", None, None, 1, "*/15 * * * * run.sh"),
    ("hourly", "00:20", None, 1, "20 * * * * run.sh"),
    ("2h", "00:10", None, 1, "10 */2 * * * run.sh"),
    ("daily", "08:30", None, 1, "30 8 * * * run.sh"),
    ("weekly", "02:30", "mon,wed,fri", 1, "30 2 * * MON,WED,FRI run.sh"),
    ("monthly", "06:00", None, 15, "0 6 15 * * run.sh")])
def test_cron(every, at, days, dom, expected):
    entry = tsh.cron_entry(sched(every, at, days, dom), "run.sh", None)
    assert entry.splitlines()[-1] == expected


def test_cron_log_is_quoted():
    entry = tsh.cron_entry(sched("daily"), "run.sh", "/tmp/my log.txt")
    assert entry.endswith(">> '/tmp/my log.txt' 2>&1")


def test_schtasks():
    line = tsh.schtasks_entry(sched("weekly", "02:30", "mon,fri"), "python C:\\b.py", "bk",
                              None).splitlines()[-1]
    assert line == ('schtasks /Create /TN "bk" /TR "python C:\\b.py" '
                    "/SC WEEKLY /D MON,FRI /ST 02:30 /F")
    assert "/SC MINUTE /MO 10" in tsh.schtasks_entry(sched("10m"), "x", "t", None)
    assert "/SC MONTHLY /D 3 /ST 09:00" in tsh.schtasks_entry(sched("monthly", dom=3), "x", "t",
                                                              None)
    quoted = tsh.schtasks_entry(sched("daily"), 'python "C:\\my dir\\b.py"', "t", "C:\\log.txt")
    assert '/TR "cmd /c python \\"C:\\my dir\\b.py\\" >> \\"C:\\log.txt\\" 2>&1"' in quoted


def plist_of(entry):
    return ET.fromstring(entry[entry.index("<?xml"):].split("?>", 1)[1])


def test_launchd_calendar_and_interval():
    weekly = tsh.launchd_entry(sched("weekly", "02:30", "mon,sun"), "/usr/bin/python3 b.py & x",
                               "bk", "/tmp/o.log")
    root = plist_of(weekly)  # must be well-formed XML even with an ampersand in the command
    strings = [e.text for e in root.iter("string")]
    assert "com.user.bk" in strings and "b.py" in strings and "&" in strings
    outer = list(root.find("dict"))
    calendar = outer[[c.text for c in outer].index("StartCalendarInterval") + 1]
    schedule = [{inner[i].text: int(inner[i + 1].text) for i in range(0, len(inner), 2)}
                for inner in calendar]
    assert [e["Weekday"] for e in schedule] == [1, 0]  # Monday is 1, Sunday is 0 in launchd
    assert all((e["Hour"], e["Minute"]) == (2, 30) for e in schedule)
    assert "launchctl load" in weekly.splitlines()[0]
    assert "<key>StandardOutPath</key>" in weekly
    interval = tsh.launchd_entry(sched("2h"), "run.sh", "x", None)
    assert "<key>StartInterval</key>\n  <integer>7200</integer>" in interval
    assert "StandardOutPath" not in interval


def test_systemd():
    assert [tsh.systemd_calendar(sched(*a)) for a in (
        ("15m",), ("hourly", "00:05"), ("3h", "00:10"), ("daily", "08:30"),
        ("weekly", "02:30", "mon,fri"))] == [
        "*:0/15", "*:05:00", "0/3:10:00", "*-*-* 08:30:00", "Mon,Fri *-*-* 02:30:00"]
    assert tsh.systemd_calendar(sched("monthly", "06:00", dom=7)) == "*-*-07 06:00:00"
    entry = tsh.systemd_entry(sched("daily", "08:30"), "python3 'my script.py' --x", "bk", "/v/l")
    assert "ExecStart=python3 'my script.py' --x" in entry and "OnCalendar=*-*-* 08:30:00" in entry
    assert "StandardOutput=append:/v/l" in entry and "enable --now bk.timer" in entry


def test_cli(capsys):
    assert tsh.main(["--command", "python backup.py", "--name", "nightly", "--every", "weekly",
                     "--days", "mon,fri", "--at", "02:30", "--target", "all"]) == 0
    out = capsys.readouterr().out
    assert "Schedule: every Mon, Fri at 02:30" in out and "Nothing has been installed" in out
    for marker in ("cron ====", "schtasks ====", "launchd ====", "systemd ===="):
        assert marker in out
    assert tsh.main(["--command", "x.sh", "--every", "15m", "--target", "cron"]) == 0
    assert "*/15 * * * * x.sh" in capsys.readouterr().out


def test_cli_rejects_bad_input():
    for argv in (["--command", " "], ["--command", "x", "--name", "bad name"],
                 ["--command", "x", "--every", "yearly"], ["--command", "x", "--at", "9"],
                 ["--command", "unterminated 'quote", "--target", "systemd"]):
        with pytest.raises(SystemExit):
            tsh.main(argv)
