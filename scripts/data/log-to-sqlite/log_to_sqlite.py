"""Load web-server access logs and application logs into SQLite so you can query them with SQL."""
import argparse
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ACCESS = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] "(?P<request>[^"]*)" (?P<status>\d{3}) '
    r'(?P<bytes>\S+)(?: "(?P<referrer>[^"]*)" "(?P<agent>[^"]*)")?')
APP = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[,.]\d+)?)\s+(?P<level>[A-Za-z]+)\s+"
    r"(?:\[(?P<component>[^\]]+)\]\s*)?(?P<message>.*)$")
EXCEPTION = re.compile(r"^[\w.]*(Error|Exception|Warning)\b.*")
LEVELS = {"WARN": "WARNING", "ERR": "ERROR", "FATAL": "CRITICAL"}
SCHEMA = {
    "access_logs": "CREATE TABLE access_logs (id INTEGER PRIMARY KEY, source TEXT, "
                   "line_no INTEGER, ip TEXT, ts TEXT, method TEXT, path TEXT, protocol TEXT, "
                   "status INTEGER, bytes INTEGER, referrer TEXT, agent TEXT)",
    "app_logs": "CREATE TABLE app_logs (id INTEGER PRIMARY KEY, source TEXT, line_no INTEGER, "
                "ts TEXT, level TEXT, component TEXT, message TEXT)",
}


def access_time(text):
    """'10/Nov/2026:09:00:06 +0000' -> '2026-11-10T09:00:06'."""
    try:
        return datetime.strptime(text.split()[0], "%d/%b/%Y:%H:%M:%S").isoformat()
    except ValueError:
        return text


def app_time(text):
    text = text.replace(",", ".").replace(" ", "T")
    return text.split(".")[0]


def parse_line(line):
    """Return ('access' | 'app', fields dict) or None when the line isn't a known format."""
    match = ACCESS.match(line)
    if match:
        parts = match["request"].split()
        sent = match["bytes"]
        return "access", {
            "ip": match["ip"], "ts": access_time(match["ts"]),
            "method": parts[0] if parts else "", "path": parts[1] if len(parts) > 1 else "",
            "protocol": parts[2] if len(parts) > 2 else "", "status": int(match["status"]),
            "bytes": int(sent) if sent.isdigit() else 0, "referrer": match["referrer"] or "",
            "agent": match["agent"] or ""}
    match = APP.match(line)
    if match and match["level"].upper() in {
            "TRACE", "DEBUG", "INFO", "NOTICE", "WARN", "WARNING", "ERROR", "ERR", "CRITICAL",
            "FATAL"}:
        level = match["level"].upper()
        return "app", {"ts": app_time(match["ts"]), "level": LEVELS.get(level, level),
                       "component": match["component"] or "", "message": match["message"].strip()}
    return None


def load(path):
    """Parse a log file. Return (access rows, app rows, count of unparsed lines)."""
    access, app, unparsed = [], [], 0
    for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(),
                                  1):
        if not line.strip():
            continue
        parsed = parse_line(line)
        if parsed is None:
            trace = line[:1] in (" ", "\t") or line.startswith(("Traceback", "at ", "Caused by"))
            if app and (trace or EXCEPTION.match(line)):
                app[-1][1]["message"] += "\n" + line.strip()  # stack trace continuation
            else:
                unparsed += 1
            continue
        kind, fields = parsed
        (access if kind == "access" else app).append((number, fields))
    return access, app, unparsed


def create_tables(con, replace):
    for name, sql in SCHEMA.items():
        if replace:
            con.execute(f"DROP TABLE IF EXISTS {name}")
        con.execute(sql.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS", 1))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Load log files into a SQLite database.")
    parser.add_argument("logs", nargs="+", type=Path, help="access logs and/or application logs")
    parser.add_argument("--db", type=Path, required=True, help="SQLite database file")
    parser.add_argument("--replace", action="store_true",
                        help="start the log tables from scratch instead of adding to them")
    parser.add_argument("--apply", action="store_true",
                        help="really write to the database (default is a dry run)")
    args = parser.parse_args(argv)
    for path in args.logs:
        if not path.is_file():
            parser.error(f"not a file: {path}")

    parsed, totals = [], [0, 0, 0]
    for path in args.logs:
        access, app, unparsed = load(path)
        parsed.append((path, access, app))
        print(f"{path.name}: {len(access)} access line(s), {len(app)} application line(s)"
              + (f", {unparsed} not recognised" if unparsed else ""))
        totals = [totals[0] + len(access), totals[1] + len(app), totals[2] + unparsed]
    if not args.apply:
        print(f"\nDry run: would add {totals[0]} row(s) to access_logs and {totals[1]} to "
              f"app_logs in {args.db}. Use --apply to do it.")
        return 0 if totals[0] + totals[1] else 1

    con = sqlite3.connect(args.db)
    try:
        create_tables(con, args.replace)
        for path, access, app in parsed:
            con.executemany(
                "INSERT INTO access_logs (source, line_no, ip, ts, method, path, protocol, status, "
                "bytes, referrer, agent) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                [(path.name, n, f["ip"], f["ts"], f["method"], f["path"], f["protocol"],
                  f["status"], f["bytes"], f["referrer"], f["agent"]) for n, f in access])
            con.executemany(
                "INSERT INTO app_logs (source, line_no, ts, level, component, message) "
                "VALUES (?,?,?,?,?,?)",
                [(path.name, n, f["ts"], f["level"], f["component"], f["message"])
                 for n, f in app])
        con.commit()
        print(f"\nSaved to {args.db}:")
        for table in SCHEMA:
            print(f"  {table}: {con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]} row(s)")
        for level, count in con.execute("SELECT level, COUNT(*) FROM app_logs GROUP BY level "
                                        "ORDER BY COUNT(*) DESC"):
            print(f"    {level:<9} {count}")
        top = con.execute("SELECT status, COUNT(*) FROM access_logs GROUP BY status "
                          "ORDER BY COUNT(*) DESC LIMIT 4").fetchall()
        if top:
            print("    status codes: " + ", ".join(f"{s} x{c}" for s, c in top))
        print("\nTry: sqlite_query_cli.py " + str(args.db) + " \"SELECT path, COUNT(*) FROM "
              "access_logs WHERE status >= 500 GROUP BY path\"")
    except sqlite3.Error as err:
        print(f"Database error: {err}", file=sys.stderr)
        con.rollback()
        return 1
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
