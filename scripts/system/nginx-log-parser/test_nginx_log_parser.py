import csv
import io

import nginx_log_parser as nlp
import pytest

COMBINED = ('203.0.113.7 - alice [10/Nov/2026:09:15:02 +0000] "GET /products/42?x=1 HTTP/1.1" 200 '
            '5123 "https://example.com/" "Mozilla/5.0 (X11; Linux) Firefox/120.0"')
COMMON = '198.51.100.23 - - [10/Nov/2026:09:16:00 +0100] "POST /api/orders HTTP/1.1" 500 -'
BAD_REQUEST = '192.0.2.5 - - [10/Nov/2026:09:17:00 +0000] "-" 400 0 "-" "-"'
LOG = "\n".join([
    COMBINED, COMMON, BAD_REQUEST,
    '203.0.113.7 - - [10/Nov/2026:09:18:00 +0000] "GET /missing HTTP/2.0" 404 153 "-" "curl/8.4"',
    "this line is not an access log entry", ""])


def test_parse_combined_line():
    row = nlp.parse_line(COMBINED)
    assert row == {"time": "2026-11-10T09:15:02+00:00", "ip": "203.0.113.7", "method": "GET",
                   "path": "/products/42?x=1", "protocol": "HTTP/1.1", "status": 200,
                   "bytes": 5123, "referrer": "https://example.com/",
                   "user_agent": "Mozilla/5.0 (X11; Linux) Firefox/120.0", "user": "alice"}


def test_parse_common_format_dash_bytes_and_timezone():
    row = nlp.parse_line(COMMON)
    assert row["bytes"] == 0 and row["referrer"] == "" and row["user_agent"] == ""
    assert row["time"] == "2026-11-10T09:16:00+01:00" and row["user"] == ""


def test_malformed_requests_and_garbage():
    row = nlp.parse_line(BAD_REQUEST)
    assert row["method"] == "" and row["path"] == "" and row["status"] == 400
    assert nlp.parse_line("not a log line") is None
    assert nlp.parse_line('1.2.3.4 - - [99/Nov/2026:99:99:99 +0000] "GET / HTTP/1.1" 200 1') is None
    escaped = nlp.parse_line('1.2.3.4 - - [10/Nov/2026:09:00:00 +0000] "GET / HTTP/1.1" 200 1 '
                             '"-" "agent \\"quoted\\" text"')
    assert escaped["user_agent"] == 'agent \\"quoted\\" text'


@pytest.mark.parametrize("status,count", [
    (None, 4), ("404", 1), ("4xx", 2), ("5xx", 1), ("2xx", 1)])
def test_status_filters(tmp_path, status, count):
    path = tmp_path / "access.log"
    path.write_text(LOG)
    rows, bad = nlp.read_rows([path], status=status)
    assert len(rows) == count and bad == 1


def test_other_filters(tmp_path):
    path = tmp_path / "access.log"
    path.write_text(LOG)
    assert len(nlp.read_rows([path], path_contains="/api")[0]) == 1
    assert [r["path"] for r in nlp.read_rows([path], method="get")[0]] == [
        "/products/42?x=1", "/missing"]


def test_cli_prints_csv_with_a_summary_on_stderr(tmp_path, capsys):
    path = tmp_path / "access.log"
    path.write_text(LOG)
    assert nlp.main([str(path), "--columns", "ip,status,path"]) == 0
    captured = capsys.readouterr()
    rows = list(csv.DictReader(io.StringIO(captured.out)))
    assert rows[0] == {"ip": "203.0.113.7", "status": "200", "path": "/products/42?x=1"}
    assert len(rows) == 4
    assert "4 row(s) written; 1 line(s) weren't in access-log format" in captured.err


def test_cli_writes_a_new_file_and_never_overwrites(tmp_path, capsys):
    path, out = tmp_path / "access.log", tmp_path / "out.csv"
    path.write_text(LOG)
    assert nlp.main([str(path), "--out", str(out), "--status", "5xx"]) == 0
    saved = list(csv.DictReader(out.open(encoding="utf-8")))
    assert [r["status"] for r in saved] == ["500"] and "written to" in capsys.readouterr().out
    out.write_text("keep")
    assert nlp.main([str(path), "--out", str(out)]) == 1 and out.read_text() == "keep"


def test_no_matching_rows_exit_one_and_bad_arguments(tmp_path, capsys):
    path = tmp_path / "access.log"
    path.write_text(LOG)
    assert nlp.main([str(path), "--status", "301"]) == 1
    for args in (["--columns", "ip,nope"], ["--status", "teapot"], ["--columns", ","]):
        with pytest.raises(SystemExit):
            nlp.main([str(path), *args])
    assert nlp.main([str(tmp_path / "gone.log")]) == 1
