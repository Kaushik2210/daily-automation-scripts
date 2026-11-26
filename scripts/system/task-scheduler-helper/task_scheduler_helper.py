"""Generate cron, Task Scheduler, launchd or systemd entries to run a command on a schedule."""
import argparse
import platform
import re
import shlex
import sys
from xml.sax.saxutils import escape

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
CRON_DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
SYSTEMD_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def parse_schedule(every, at, days, day_of_month):
    """Return {kind, n, hour, minute, days, dom}. kind: minutes, hours, daily, weekly, monthly."""
    hour, minute = 9, 0
    if at:
        match = re.fullmatch(r"(\d{1,2}):(\d{2})", at)
        if not match or int(match.group(1)) > 23 or int(match.group(2)) > 59:
            raise ValueError(f"--at must look like 08:30, got '{at}'")
        hour, minute = int(match.group(1)), int(match.group(2))
    every = every.lower()
    schedule = {"kind": None, "n": 1, "hour": hour, "minute": minute, "days": [], "dom": 1}
    interval = re.fullmatch(r"(\d+)\s*(m|min|h|hour|hours)", every)
    if interval:
        n, unit = int(interval.group(1)), interval.group(2)
        schedule["kind"] = "minutes" if unit in ("m", "min") else "hours"
        limit = 59 if schedule["kind"] == "minutes" else 23
        if not 1 <= n <= limit:
            raise ValueError(f"every {n}{unit[0]} isn't valid; use 1-{limit} "
                             f"({'switch to hours' if limit == 59 else 'use daily'} beyond that)")
        schedule["n"] = n
    elif every == "hourly":
        schedule.update(kind="hours", n=1)
    elif every in ("daily", "weekly", "monthly"):
        schedule["kind"] = every
    else:
        raise ValueError(f"--every must be like 15m, 2h, hourly, daily, weekly or monthly; "
                         f"got '{every}'")
    if schedule["kind"] == "weekly":
        names = [d.strip().lower()[:3] for d in (days or "mon").split(",") if d.strip()]
        bad = [d for d in names if d not in DAYS]
        if bad or not names:
            raise ValueError(f"--days must be like mon,wed,fri; got '{days}'")
        schedule["days"] = sorted({DAYS.index(d) for d in names})
    if schedule["kind"] == "monthly":
        if not 1 <= day_of_month <= 28:
            raise ValueError("--day-of-month must be 1-28 (so it exists every month)")
        schedule["dom"] = day_of_month
    return schedule


def explain(s):
    time_text = f"{s['hour']:02d}:{s['minute']:02d}"
    return {"minutes": f"every {s['n']} minute(s)", "hours": f"every {s['n']} hour(s)",
            "daily": f"every day at {time_text}",
            "weekly": f"every {', '.join(DAYS[d].title() for d in s['days'])} at {time_text}",
            "monthly": f"on day {s['dom']} of every month at {time_text}"}[s["kind"]]


def cron_entry(s, command, log):
    fields = {"minutes": f"*/{s['n']} * * * *",
              "hours": f"{s['minute']} " + (f"*/{s['n']}" if s["n"] > 1 else "*") + " * * *",
              "daily": f"{s['minute']} {s['hour']} * * *",
              "weekly": f"{s['minute']} {s['hour']} * * "
                        + ",".join(CRON_DAYS[d] for d in s["days"]),
              "monthly": f"{s['minute']} {s['hour']} {s['dom']} * *"}[s["kind"]]
    tail = f" >> {shlex.quote(log)} 2>&1" if log else ""
    return (f"# Add with: crontab -e   (list with: crontab -l)\n{fields} {command}{tail}")


def schtasks_entry(s, command, name, log):
    action = f'cmd /c {command} >> "{log}" 2>&1' if log else command
    run = action.replace('"', '\\"')
    base = f'schtasks /Create /TN "{name}" /TR "{run}"'
    time_text = f"{s['hour']:02d}:{s['minute']:02d}"
    schedule = {"minutes": f"/SC MINUTE /MO {s['n']}", "hours": f"/SC HOURLY /MO {s['n']}",
                "daily": f"/SC DAILY /ST {time_text}",
                "weekly": f"/SC WEEKLY /D {','.join(CRON_DAYS[d] for d in s['days'])} "
                          f"/ST {time_text}",
                "monthly": f"/SC MONTHLY /D {s['dom']} /ST {time_text}"}[s["kind"]]
    return (f"REM Run in a Command Prompt. Remove later with: schtasks /Delete /TN \"{name}\"\n"
            f"{base} {schedule} /F")


def launchd_entry(s, command, name, log):
    label = f"com.user.{name}"
    items = "".join(f"\n    <string>{escape(part)}</string>" for part in shlex.split(command))
    if s["kind"] in ("minutes", "hours"):
        seconds = s["n"] * (60 if s["kind"] == "minutes" else 3600)
        when = f"  <key>StartInterval</key>\n  <integer>{seconds}</integer>"
    else:
        keys = {"Hour": s["hour"], "Minute": s["minute"]}
        if s["kind"] == "monthly":
            keys["Day"] = s["dom"]
        if s["kind"] == "weekly":
            entries = [{**keys, "Weekday": (d + 1) % 7} for d in s["days"]]
        else:
            entries = [keys]
        blocks = "".join("\n    <dict>" + "".join(f"<key>{k}</key><integer>{v}</integer>"
                                                  for k, v in e.items()) + "</dict>"
                         for e in entries)
        when = f"  <key>StartCalendarInterval</key>\n  <array>{blocks}\n  </array>"
    out = (f'  <key>StandardOutPath</key>\n  <string>{escape(log)}</string>\n'
           f'  <key>StandardErrorPath</key>\n  <string>{escape(log)}</string>\n' if log else "")
    return (f"# Save as ~/Library/LaunchAgents/{label}.plist, then: launchctl load "
            f"~/Library/LaunchAgents/{label}.plist\n"
            '<?xml version="1.0" encoding="UTF-8"?>\n<plist version="1.0">\n<dict>\n'
            f"  <key>Label</key>\n  <string>{label}</string>\n"
            f"  <key>ProgramArguments</key>\n  <array>{items}\n  </array>\n{when}\n{out}"
            "</dict>\n</plist>")


def systemd_calendar(s):
    time_text = f"{s['hour']:02d}:{s['minute']:02d}:00"
    return {"minutes": f"*:0/{s['n']}", "hours": f"0/{s['n']}:{s['minute']:02d}:00"
            if s["n"] > 1 else f"*:{s['minute']:02d}:00",
            "daily": f"*-*-* {time_text}",
            "weekly": f"{','.join(SYSTEMD_DAYS[d] for d in s['days'])} *-*-* {time_text}",
            "monthly": f"*-*-{s['dom']:02d} {time_text}"}[s["kind"]]


def systemd_entry(s, command, name, log):
    exec_line = " ".join(shlex.quote(p) for p in shlex.split(command))
    output = f"StandardOutput=append:{log}\nStandardError=append:{log}\n" if log else ""
    return (f"# Save as ~/.config/systemd/user/{name}.service\n[Unit]\nDescription={name}\n\n"
            f"[Service]\nType=oneshot\nExecStart={exec_line}\n{output}\n"
            f"# Save as ~/.config/systemd/user/{name}.timer\n[Unit]\nDescription=Run {name}\n\n"
            f"[Timer]\nOnCalendar={systemd_calendar(s)}\nPersistent=true\n\n"
            f"[Install]\nWantedBy=timers.target\n\n"
            f"# Then: systemctl --user daemon-reload && systemctl --user enable --now {name}.timer")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate scheduler entries for a command.")
    parser.add_argument("--command", required=True,
                        help="the command to run, e.g. 'python backup.py'")
    parser.add_argument("--name", default="my-task",
                        help="task name: letters, digits, - _ . (my-task)")
    parser.add_argument("--every", default="daily",
                        help="15m, 2h, hourly, daily, weekly or monthly (daily)")
    parser.add_argument("--at", help="time of day, HH:MM (09:00); hourly uses only the minute")
    parser.add_argument("--days", help="weekdays for weekly, e.g. mon,wed,fri")
    parser.add_argument("--day-of-month", type=int, default=1, help="day for monthly, 1-28 (1)")
    parser.add_argument("--log", help="append the command's output to this file")
    parser.add_argument("--target", default="auto",
                        choices=["auto", "cron", "schtasks", "launchd", "systemd", "all"],
                        help="which scheduler to write for (auto = this system's)")
    args = parser.parse_args(argv)
    if not args.command.strip():
        parser.error("--command can't be empty")
    if not re.fullmatch(r"[\w.-]+", args.name):
        parser.error("--name may only contain letters, digits, '-', '_' and '.'")
    try:
        schedule = parse_schedule(args.every, args.at, args.days, args.day_of_month)
        if args.target in ("launchd", "systemd", "all"):
            shlex.split(args.command)
    except ValueError as err:
        parser.error(str(err))

    target = args.target
    if target == "auto":
        target = {"Windows": "schtasks", "Darwin": "launchd"}.get(platform.system(), "cron")
    makers = {"cron": lambda: cron_entry(schedule, args.command, args.log),
              "schtasks": lambda: schtasks_entry(schedule, args.command, args.name, args.log),
              "launchd": lambda: launchd_entry(schedule, args.command, args.name, args.log),
              "systemd": lambda: systemd_entry(schedule, args.command, args.name, args.log)}
    print(f"Schedule: {explain(schedule)}\nNothing has been installed; copy what you need.\n")
    chosen = list(makers) if target == "all" else [target]
    for number, key in enumerate(chosen):
        if len(chosen) > 1:
            print(f"{'=' * 12} {key} {'=' * 12}")
        print(makers[key]() + ("\n" if number < len(chosen) - 1 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
