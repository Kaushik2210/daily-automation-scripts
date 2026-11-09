import csv
import io
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import issue_exporter as ie
import pytest


def issue(number, title="T", state="open", labels=(), pr=False, **extra):
    item = {"number": number, "title": title, "state": state, "user": {"login": "ann"},
            "labels": [{"name": n} for n in labels], "assignees": [{"login": "bob"}],
            "comments": 2, "created_at": "2026-10-01T09:00:00Z",
            "updated_at": "2026-10-02T09:00:00Z", "closed_at": None,
            "html_url": f"https://github.com/o/r/issues/{number}", **extra}
    if pr:
        item["pull_request"] = {}
    return item


ISSUES = [issue(1, "Bug, with comma", labels=["bug", "Priority: High"]),
          issue(2, "A PR", pr=True), issue(3, 'Quote "here"', "closed", ["docs"]),
          issue(4, "Another", labels=["bug"])]


def test_to_row_flattens_nested_fields():
    row = ie.to_row(ISSUES[0])
    assert row["author"] == "ann" and row["assignees"] == "bob"
    assert row["labels"] == "bug;Priority: High" and row["created"] == "2026-10-01"
    assert row["closed"] == ""
    assert ie.to_row({})["number"] is None


def test_filters_drop_prs_and_match_state_and_all_labels():
    def numbers(**kw):
        return [i["number"] for i in ie.filter_issues(ISSUES, **kw)]

    assert numbers() == [1, 3, 4]
    assert numbers(include_prs=True) == [1, 2, 3, 4]
    assert numbers(state="closed") == [3]
    assert numbers(labels=["BUG"]) == [1, 4]
    assert numbers(labels=["bug", "priority: high"]) == [1]


def test_csv_round_trips_commas_and_quotes():
    rows = list(csv.DictReader(io.StringIO(ie.to_csv(ISSUES))))
    assert [r["title"] for r in rows] == ["Bug, with comma", "A PR", 'Quote "here"', "Another"]
    assert list(rows[0]) == ie.COLUMNS


def test_cli_prints_or_writes_a_new_file(tmp_path, capsys):
    src, out = tmp_path / "issues.json", tmp_path / "issues.csv"
    src.write_text(json.dumps(ISSUES))
    assert ie.main(["--from-file", str(src), "--state", "open"]) == 0
    printed = capsys.readouterr().out
    assert printed.splitlines()[0].startswith("number,title,state")
    assert [r["number"] for r in csv.DictReader(io.StringIO(printed))] == ["1", "4"]
    assert ie.main(["--from-file", str(src), "--out", str(out), "--label", "bug"]) == 0
    assert "Wrote 2 issue(s)" in capsys.readouterr().out
    out.write_text("keep")
    assert ie.main(["--from-file", str(src), "--out", str(out)]) == 1
    assert out.read_text() == "keep"


def test_bad_input(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text('{"message": "Not Found"}')
    assert ie.main(["--from-file", str(bad)]) == 1
    assert "isn't a list" in capsys.readouterr().err
    bad.write_text("{oops")
    assert ie.main(["--from-file", str(bad)]) == 1
    with pytest.raises(SystemExit):
        ie.main([])
    with pytest.raises(SystemExit):
        ie.main(["not-a-repo"])


class Handler(BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        Handler.seen.append(self.path)
        host = f"http://127.0.0.1:{self.server.server_address[1]}"
        if "page=2" in self.path:
            body, link = [ISSUES[3]], ""
        elif self.path.startswith("/repos/o/r/issues"):
            body, link = ISSUES[:3], f'<{host}/repos/o/r/issues?page=2>; rel="next"'
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        if link:
            self.send_header("Link", link)
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())


@pytest.fixture
def server(monkeypatch):
    Handler.seen = []
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    monkeypatch.setattr(ie, "API", f"http://127.0.0.1:{httpd.server_address[1]}")
    yield httpd
    httpd.shutdown()


def test_live_export_follows_paging(server, capsys):
    assert ie.main(["o/r"]) == 0
    out = capsys.readouterr().out
    assert "Another" in out and "A PR" not in out
    assert len(Handler.seen) == 2 and "state=all" in Handler.seen[0]
    assert ie.main(["o/r", "--max-pages", "1"]) == 0
    assert "Another" not in capsys.readouterr().out


def test_live_404_has_a_helpful_message(server, capsys):
    assert ie.main(["o/missing"]) == 1
    assert "repository not found" in capsys.readouterr().err
