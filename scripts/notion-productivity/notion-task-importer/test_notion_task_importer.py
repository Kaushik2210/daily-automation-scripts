import json
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import notion_task_importer as nti
import pytest

TODAY = date(2026, 11, 9)
TEXT = """# my tasks
- [ ] Write report @2026-11-18 #work !high
- [x] Send invoice #work
Call plumber @tomorrow
* Water plants #home #garden @+3d !low
- [ ]
# not a tag line
"""


def test_resolve_date_words():
    assert nti.resolve_date("today", TODAY) == TODAY
    assert nti.resolve_date("Tomorrow", TODAY) == date(2026, 11, 10)
    assert nti.resolve_date("+3d", TODAY) == date(2026, 11, 12)
    assert nti.resolve_date("2026-12-24", TODAY) == date(2026, 12, 24)
    with pytest.raises(ValueError):
        nti.resolve_date("someday", TODAY)


def test_parse_tasks_reads_markers_and_cleans_titles():
    tasks = nti.parse_tasks(TEXT, TODAY)
    assert [t["title"] for t in tasks] == [
        "Write report", "Send invoice", "Call plumber", "Water plants"]
    first, second, third, fourth = tasks
    assert (first["due"], first["tags"], first["priority"], first["done"]) == (
        "2026-11-18", ["work"], "high", False)
    assert second["done"] is True and second["tags"] == ["work"] and second["due"] == ""
    assert third["due"] == "2026-11-10"
    assert fourth["tags"] == ["home", "garden"] and fourth["due"] == "2026-11-12"
    assert fourth["priority"] == "low"


def test_unknown_markers_stay_in_the_title():
    task = nti.parse_tasks("Meet @someone about #1 !urgent", TODAY)[0]
    assert task["title"] == "Meet @someone about !urgent"
    assert task["tags"] == ["1"]


def page(name):
    return {"properties": {
        "Name": {"type": "title", "title": [{"plain_text": name}]},
        "Status": {"type": "select"}, "Due": {"type": "date"}, "Tags": {"type": "multi_select"}}}


EXISTING = {"results": [page("send invoice")]}


def test_build_properties_uses_available_columns_and_status_words():
    names = {"title": "Name", "status": "Status", "date": "Due", "tags": "Tags",
             "priority": "Priority"}
    types = {"Name": "title", "Status": "select", "Due": "date", "Tags": "multi_select"}
    task = nti.parse_tasks("- [x] Ship it @2026-11-20 #work !high", TODAY)[0]
    props = nti.build_properties(task, names, types, ("Not started", "Done"))
    assert props["Status"] == {"select": {"name": "Done"}}
    assert props["Due"] == {"date": {"start": "2026-11-20"}}
    assert props["Tags"] == {"multi_select": [{"name": "work"}]}
    assert "Priority" not in props  # the database has no such property
    types["Status"] = "checkbox"
    assert nti.build_properties(task, names, types, ("a", "b"))["Status"] == {"checkbox": True}


def test_dry_run_from_a_saved_database(tmp_path, capsys):
    f, existing = tmp_path / "tasks.txt", tmp_path / "db.json"
    f.write_text(TEXT)
    existing.write_text(json.dumps(EXISTING))
    assert nti.main([str(f), "--existing", str(existing), "--today", "2026-11-09"]) == 0
    out = capsys.readouterr().out
    assert "4 task(s) in the file: 3 to add, 1 already in Notion." in out
    assert "+ Write report  [due 2026-11-18, tags work, priority high]" in out
    assert "= Send invoice  (already there)" in out and "Dry run" in out
    assert "No such property in the database (ignored): Priority" in out


def test_argument_errors(tmp_path, capsys):
    f, existing = tmp_path / "tasks.txt", tmp_path / "db.json"
    f.write_text("a")
    existing.write_text(json.dumps(EXISTING))
    for args in ([str(f)], [str(f), "--existing", str(existing), "--apply"],
                 [str(tmp_path / "gone.txt"), "--existing", str(existing)]):
        with pytest.raises(SystemExit):
            nti.main(args)
    assert nti.main([str(f), "--existing", str(existing), "--title-prop", "Task"]) == 1
    assert "no title property called 'Task'" in capsys.readouterr().err


class Fake(BaseHTTPRequestHandler):
    created = []

    def log_message(self, *args):
        pass

    def reply(self, body, code=200):
        self.send_response(code)
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def do_GET(self):
        props = {"Name": {"type": "title"}, "Status": {"type": "select"}, "Due": {"type": "date"},
                 "Tags": {"type": "multi_select"}}
        self.reply({"properties": props} if self.path == "/databases/db1" else {}, 200
                   if self.path == "/databases/db1" else 404)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path.endswith("/query"):
            self.reply({"results": EXISTING["results"], "has_more": False})
        else:
            Fake.created.append(body)
            self.reply({"id": "new"})


def test_apply_creates_only_the_new_tasks(monkeypatch, tmp_path, capsys):
    Fake.created = []
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    monkeypatch.setattr(nti, "API", f"http://127.0.0.1:{httpd.server_address[1]}")
    monkeypatch.setenv("NOTION_TOKEN", "secret_x")
    f = tmp_path / "tasks.txt"
    f.write_text(TEXT)
    try:
        args = [str(f), "--db", "db1", "--today", "2026-11-09", "--delay", "0"]
        assert nti.main(args) == 0 and Fake.created == []  # dry run
        assert nti.main([*args, "--apply"]) == 0
    finally:
        httpd.shutdown()
    titles = [c["properties"]["Name"]["title"][0]["text"]["content"] for c in Fake.created]
    assert titles == ["Write report", "Call plumber", "Water plants"]
    assert all(c["parent"] == {"database_id": "db1"} for c in Fake.created)
    assert Fake.created[0]["properties"]["Status"] == {"select": {"name": "Not started"}}
    assert "Added 3 task(s)." in capsys.readouterr().out
