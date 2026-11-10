import json
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import notion_db_backup as ndb
import pytest


def t(s):
    return {"plain_text": s}


PAGES = [{"id": "p1", "url": "https://n.so/p1", "created_time": "c", "last_edited_time": "e",
          "properties": {
              "Name": {"type": "title", "title": [t("Write "), t("report")]},
              "Status": {"type": "select", "select": {"name": "Open"}},
              "Tags": {"type": "multi_select", "multi_select": [{"name": "a"}, {"name": "b"}]},
              "Due": {"type": "date", "date": {"start": "2026-01-01", "end": "2026-01-03"}},
              "Done": {"type": "checkbox", "checkbox": False},
              "N": {"type": "number", "number": 4.5},
              "Who": {"type": "people", "people": [{"name": "Ann"}, {"id": "u2"}]},
              "Rel": {"type": "relation", "relation": [{"id": "r1"}]},
              "F": {"type": "formula", "formula": {"type": "string", "string": "calc"}},
              "ID": {"type": "unique_id", "unique_id": {"prefix": "TASK", "number": 7}},
              "Empty": {"type": "select", "select": None},
              "Odd": {"type": "rollup", "rollup": {}}}},
         {"id": "p2", "properties": {"Name": {"type": "title", "title": []}}}]


def test_simple_value_covers_the_property_types():
    row = ndb.simplify(PAGES)[0]["properties"]
    assert row == {"Name": "Write report", "Status": "Open", "Tags": ["a", "b"],
                   "Due": "2026-01-01 -> 2026-01-03", "Done": False, "N": 4.5,
                   "Who": ["Ann", "u2"], "Rel": ["r1"], "F": "calc", "ID": "TASK7",
                   "Empty": None, "Odd": None}
    assert ndb.simple_value({"type": "date", "date": {"start": "2026-02-02", "end": None}}) == (
        "2026-02-02")
    assert ndb.simple_value({"type": "date", "date": None}) is None


def test_default_name():
    assert ndb.default_name("0123-abcd-ef45-6789", datetime(2026, 11, 9)) == (
        "notion-backup-0123abcd-20261109.json")
    assert ndb.default_name("", datetime(2026, 11, 9)) == "notion-backup-db-20261109.json"


def test_from_file_writes_a_new_file_and_never_overwrites(tmp_path, capsys):
    src, out = tmp_path / "query.json", tmp_path / "backup.json"
    src.write_text(json.dumps({"results": PAGES}))
    assert ndb.main(["--from-file", str(src), "--out", str(out), "--format", "simple"]) == 0
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["page_count"] == 2 and saved["rows"][0]["properties"]["Name"] == "Write report"
    assert "Saved 2 page(s)" in capsys.readouterr().out
    out.write_text("keep")
    assert ndb.main(["--from-file", str(src), "--out", str(out)]) == 1
    assert out.read_text() == "keep"


def test_raw_format_keeps_everything_and_stdout_mode(tmp_path, capsys):
    src = tmp_path / "query.json"
    src.write_text(json.dumps({"results": PAGES}))
    assert ndb.main(["--from-file", str(src), "--stdout"]) == 0
    dumped = json.loads(capsys.readouterr().out)
    assert dumped["pages"] == PAGES and dumped["database"] is None
    assert not list(tmp_path.glob("notion-backup-*"))


def test_bad_input(tmp_path, capsys):
    with pytest.raises(SystemExit):
        ndb.main([])
    bad = tmp_path / "bad.json"
    bad.write_text("[]")
    assert ndb.main(["--from-file", str(bad)]) == 1
    assert "Couldn't read" in capsys.readouterr().err


class Fake(BaseHTTPRequestHandler):
    calls = []

    def log_message(self, *args):
        pass

    def reply(self, body, code=200):
        self.send_response(code)
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def do_GET(self):
        Fake.calls.append(("GET", self.path))
        self.reply({"id": "db1", "title": [t("Tasks")], "properties": {"Name": {"type": "title"}}}
                   if self.path == "/databases/db1" else {}, 200 if self.path == "/databases/db1"
                   else 404)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Fake.calls.append(("POST", self.path, body))
        first = "start_cursor" not in body
        self.reply({"results": PAGES[:1] if first else PAGES[1:], "has_more": first,
                    "next_cursor": "c2" if first else None})


@pytest.fixture
def server(monkeypatch):
    Fake.calls = []
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    monkeypatch.setattr(ndb, "API", f"http://127.0.0.1:{httpd.server_address[1]}")
    monkeypatch.setenv("NOTION_TOKEN", "secret_x")
    yield httpd
    httpd.shutdown()


def test_live_backup_pages_through_everything_and_only_reads(server, tmp_path, capsys):
    out = tmp_path / "live.json"
    assert ndb.main(["db1", "--out", str(out)]) == 0
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["page_count"] == 2 and saved["database"]["id"] == "db1"
    assert [c[0] for c in Fake.calls] == ["GET", "POST", "POST"]  # reads only, no writes
    assert Fake.calls[2][2]["start_cursor"] == "c2"


def test_live_errors(server, monkeypatch, tmp_path, capsys):
    assert ndb.main(["nope", "--out", str(tmp_path / "x.json")]) == 1
    assert "404" in capsys.readouterr().err
    monkeypatch.delenv("NOTION_TOKEN")
    assert ndb.main(["db1"]) == 1
    assert "NOTION_TOKEN" in capsys.readouterr().err
