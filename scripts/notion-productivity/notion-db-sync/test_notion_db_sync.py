import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import notion_db_sync as nds
import pytest


def text(s):
    return {"type": "text", "plain_text": s}


def page(pid, name, status="", due=None, tags=(), done=False, estimate=None):
    return {"id": pid, "properties": {
        "Name": {"type": "title", "title": [text(name)]},
        "Status": {"type": "select", "select": {"name": status} if status else None},
        "Due": {"type": "date", "date": {"start": due} if due else None},
        "Tags": {"type": "multi_select", "multi_select": [{"name": t} for t in tags]},
        "Done": {"type": "checkbox", "checkbox": done},
        "Estimate": {"type": "number", "number": estimate}}}


PAGES = [page("p1", "Report", "In progress", "2026-11-12", ["work"], False, 3),
         page("p2", "Dentist", "Not started", None, ["health", "home"], False, 1),
         page("p3", "Only in Notion", "Done", None, [], True, None)]
TYPES = nds.column_types(PAGES)


def test_prop_value_and_normalise_agree():
    for name, cell in [("Name", "Report"), ("Status", "In progress"), ("Due", "2026-11-12"),
                       ("Tags", "work"), ("Done", "no"), ("Estimate", "3.0")]:
        assert nds.normalise(TYPES[name], cell) == nds.prop_value(PAGES[0]["properties"][name])
    assert nds.normalise("multi_select", "b, a;a") == "a;b"
    assert nds.normalise("checkbox", "Yes") == "true" and nds.normalise("number", "x") == "x"


@pytest.mark.parametrize("kind,cell,expected", [
    ("title", "Hi", {"title": [{"text": {"content": "Hi"}}]}),
    ("select", "", {"select": None}), ("select", "A", {"select": {"name": "A"}}),
    ("multi_select", "a;b", {"multi_select": [{"name": "a"}, {"name": "b"}]}),
    ("date", "2026-01-02", {"date": {"start": "2026-01-02"}}), ("date", "", {"date": None}),
    ("checkbox", "true", {"checkbox": True}), ("number", "2", {"number": 2.0}),
    ("number", "", {"number": None}), ("url", "https://x.test", {"url": "https://x.test"}),
    ("rich_text", "", {"rich_text": []})])
def test_to_property(kind, cell, expected):
    assert nds.to_property(kind, cell) == expected


ROWS = [
    {"Name": "Report", "Status": "Done", "Due": "2026-11-12", "Tags": "work", "Done": "true",
     "Estimate": "3"},
    {"Name": "dentist", "Status": "Not started", "Due": "", "Tags": "home;health", "Done": "false",
     "Estimate": "1"},
    {"Name": "Brand new", "Status": "Not started", "Due": "2026-12-01", "Tags": "x",
     "Done": "false", "Estimate": "", "Mystery": "ignored"}]


def test_make_plan_creates_updates_and_leaves_the_rest():
    creates, updates, untouched, skipped = nds.make_plan(ROWS, PAGES, TYPES, "Name")
    assert [c["Name"]["title"][0]["text"]["content"] for c in creates] == ["Brand new"]
    assert "Mystery" not in creates[0] and skipped == ["Mystery"]
    assert len(updates) == 1
    page_id, name, props, fields = updates[0]
    assert (page_id, name, fields) == ("p1", "Report", ["Done", "Status"])
    assert props["Done"] == {"checkbox": True} and props["Status"] == {"select": {"name": "Done"}}
    assert untouched == 1  # "Only in Notion"


def test_title_column_and_csv_reading(tmp_path):
    assert nds.title_column(TYPES) == "Name"
    f = tmp_path / "t.csv"
    f.write_bytes("﻿Name,Status\nA,Done\n".encode())
    assert nds.read_csv(f) == [{"Name": "A", "Status": "Done"}]


def test_dry_run_from_a_saved_query(tmp_path, capsys):
    csv_file, existing = tmp_path / "t.csv", tmp_path / "db.json"
    csv_file.write_text("Name,Status,Done\nReport,Done,true\nFresh,Not started,false\n")
    existing.write_text(json.dumps({"results": PAGES}))
    assert nds.main([str(csv_file), "--existing", str(existing)]) == 0
    out = capsys.readouterr().out
    assert "1 to add, 1 to update, 2 in Notion not in the CSV" in out
    assert "+ Fresh" in out and "~ Report: Done, Status" in out and "Dry run" in out
    with pytest.raises(SystemExit):
        nds.main([str(csv_file), "--existing", str(existing), "--apply"])
    with pytest.raises(SystemExit):
        nds.main([str(csv_file)])


def test_missing_key_column(tmp_path, capsys):
    csv_file, existing = tmp_path / "t.csv", tmp_path / "db.json"
    csv_file.write_text("Status\nDone\n")
    existing.write_text(json.dumps({"results": PAGES}))
    assert nds.main([str(csv_file), "--existing", str(existing)]) == 1
    assert "needs a 'Name' column" in capsys.readouterr().err


class Fake(BaseHTTPRequestHandler):
    calls = []

    def log_message(self, *args):
        pass

    def reply(self, code, body):
        self.send_response(code)
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def do_GET(self):
        Fake.calls.append(("GET", self.path, None, self.headers.get("Authorization")))
        if self.path == "/databases/db1":
            self.reply(200, {"properties": {"Name": {"type": "title"}, "Status": {"type": "select"},
                                            "Done": {"type": "checkbox"}, "Due": {"type": "date"},
                                            "Tags": {"type": "multi_select"}}})
        else:
            self.reply(404, {})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
        Fake.calls.append(("POST", self.path, body, None))
        if self.path.endswith("/query"):
            first = "start_cursor" not in body
            self.reply(200, {"results": PAGES[:1] if first else PAGES[1:], "has_more": first,
                             "next_cursor": "c2" if first else None})
        else:
            self.reply(200, {"id": "new"})

    def do_PATCH(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Fake.calls.append(("PATCH", self.path, body, None))
        self.reply(200, {})


@pytest.fixture
def notion_server(monkeypatch):
    Fake.calls = []
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    monkeypatch.setattr(nds, "API", f"http://127.0.0.1:{httpd.server_address[1]}")
    monkeypatch.setenv("NOTION_TOKEN", "secret_x")
    yield httpd
    httpd.shutdown()


def test_live_dry_run_reads_but_never_writes(notion_server, tmp_path, capsys):
    csv_file = tmp_path / "t.csv"
    csv_file.write_text("Name,Status\nReport,Done\nFresh,Not started\n")
    assert nds.main([str(csv_file), "--db", "db1"]) == 0
    assert {c[0] for c in Fake.calls} == {"GET", "POST"} and all(
        c[1].endswith("/query") or c[1] == "/databases/db1" for c in Fake.calls)
    assert Fake.calls[0][3] == "Bearer secret_x"
    assert "1 to add, 1 to update" in capsys.readouterr().out


def test_apply_creates_and_updates(notion_server, tmp_path, capsys):
    csv_file = tmp_path / "t.csv"
    csv_file.write_text("Name,Status\nReport,Done\nFresh,Not started\n")
    assert nds.main([str(csv_file), "--db", "db1", "--apply", "--delay", "0"]) == 0
    writes = [c for c in Fake.calls if c[0] == "PATCH" or c[1] == "/pages"]
    create = next(c for c in writes if c[1] == "/pages")
    assert create[2]["parent"] == {"database_id": "db1"}
    update = next(c for c in writes if c[0] == "PATCH")
    assert update[1] == "/pages/p1" and update[2] == {"properties": {
        "Status": {"select": {"name": "Done"}}}}
    assert "Done: 1 added, 1 updated." in capsys.readouterr().out


def test_missing_token_and_unknown_database(notion_server, monkeypatch, tmp_path, capsys):
    csv_file = tmp_path / "t.csv"
    csv_file.write_text("Name\nA\n")
    assert nds.main([str(csv_file), "--db", "nope"]) == 1
    assert "404" in capsys.readouterr().err
    monkeypatch.delenv("NOTION_TOKEN")
    assert nds.main([str(csv_file), "--db", "db1"]) == 1
    assert "NOTION_TOKEN" in capsys.readouterr().err
