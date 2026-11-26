import json
import threading
from datetime import UTC, date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import weekly_github_report as wgr

BUNDLE = {
    "since": "2026-11-16T00:00:00Z", "until": "2026-11-23T00:00:00Z",
    "repos": {"me/app": {
        "commits": [
            {"sha": "a1", "author": "sam", "date": "2026-11-16T09:00:00Z", "message": "feat: x"},
            {"sha": "a2", "author": "sam", "date": "2026-11-22T23:59:00Z", "message": "fix: y"},
            {"sha": "a3", "author": "mira", "date": "2026-11-23T00:00:00Z", "message": "too late"},
            {"sha": "a4", "author": "tom", "date": "2026-11-15T23:59:00Z", "message": "too early"}],
        "pulls": [
            {"number": 1, "title": "Merged one", "user": "sam",
             "created_at": "2026-11-10T00:00:00Z", "merged_at": "2026-11-18T00:00:00Z",
             "closed_at": "2026-11-18T00:00:00Z"},
            {"number": 2, "title": "Still open", "user": "mira",
             "created_at": "2026-11-17T00:00:00Z", "merged_at": None, "closed_at": None},
            {"number": 3, "title": "Closed unmerged", "user": "tom",
             "created_at": "2026-11-17T00:00:00Z", "merged_at": None,
             "closed_at": "2026-11-19T00:00:00Z"}],
        "issues": [
            {"number": 5, "title": "Bug", "user": "lee", "labels": [],
             "created_at": "2026-11-16T10:00:00Z", "closed_at": "2026-11-20T10:00:00Z"},
            {"number": 6, "title": "Old", "user": "lee", "labels": [],
             "created_at": "2026-10-01T10:00:00Z", "closed_at": None}]}}}


def test_window_covers_the_whole_last_day():
    since, until = wgr.window(date(2026, 11, 22), 7)
    assert since == datetime(2026, 11, 16, tzinfo=UTC)
    assert until == datetime(2026, 11, 23, tzinfo=UTC)


def test_summarise_counts_only_inside_the_window():
    since, until = wgr.when(BUNDLE["since"]), wgr.when(BUNDLE["until"])
    r = wgr.summarise(BUNDLE, since, until)["me/app"]
    assert [c["sha"] for c in r["commits"]] == ["a1", "a2"] and r["authors"] == {"sam": 2}
    assert [p["number"] for p in r["prs_opened"]] == [2, 3]
    assert [p["number"] for p in r["prs_merged"]] == [1]
    assert [p["number"] for p in r["prs_open"]] == [2]
    assert [i["number"] for i in r["issues_opened"]] == [5]
    assert [i["number"] for i in r["issues_closed"]] == [5]


def test_render_has_totals_and_sections():
    since, until = wgr.when(BUNDLE["since"]), wgr.when(BUNDLE["until"])
    text, total = wgr.render(wgr.summarise(BUNDLE, since, until), since, until)
    assert text.startswith("# Weekly GitHub report: 2026-11-16 to 2026-11-22")
    assert "| me/app | 2 | 2 | 1 | 1 | 1 |" in text and total["commits"] == 2
    assert "- sam: 2 commit(s)" in text and "me/app#1 Merged one (@sam)" in text
    assert "## Still open" in text and "me/app#2 Still open" in text


def test_cli_markdown_json_and_output(tmp_path, capsys):
    saved = tmp_path / "w.json"
    saved.write_text(json.dumps(BUNDLE))
    assert wgr.main(["--from-json", str(saved)]) == 0
    assert "| **Total** | 2 | 2 | 1 | 1 | 1 |" in capsys.readouterr().out
    assert wgr.main(["--from-json", str(saved), "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["totals"]["prs_merged"] == 1 and data["repos"]["me/app"]["commits"] == 2
    out = tmp_path / "report.md"
    assert wgr.main(["--from-json", str(saved), "--output", str(out)]) == 0
    assert out.read_text().startswith("# Weekly GitHub report")
    assert wgr.main(["--from-json", str(saved), "--output", str(out)]) == 1  # never overwrites
    assert wgr.main(["--from-json", str(saved), "--week-ending", "2026-11-15"]) == 0
    earlier = capsys.readouterr().out
    assert "| **Total** | 1 | 1 | 0 | 0 | 0 |" in earlier and "- tom: 1 commit(s)" in earlier


def test_bad_input(tmp_path, capsys):
    broken = tmp_path / "b.json"
    broken.write_text('{"repos": 5}')
    assert wgr.main(["--from-json", str(broken)]) == 1
    assert "Can't build the report" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        wgr.main(["--from-json", str(broken), "--days", "0"])
    with pytest.raises(SystemExit):
        wgr.main(["--from-json", str(broken), "--week-ending", "soon"])


class FakeGitHub(BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        FakeGitHub.seen.append((self.path, self.headers.get("Authorization")))
        if "/commits" in self.path:
            body = [{"sha": "abcdef1234", "author": {"login": "sam"},
                     "commit": {"author": {"date": "2026-11-20T10:00:00Z", "name": "Sam"},
                                "message": "feat: thing\n\nlong body"}}]
        elif "/pulls" in self.path:
            body = [{"number": 9, "title": "PR", "user": {"login": "mira"},
                     "created_at": "2026-11-18T10:00:00Z", "merged_at": "2026-11-19T10:00:00Z",
                     "closed_at": "2026-11-19T10:00:00Z"}]
        else:
            body = [{"number": 3, "title": "Issue", "user": {"login": "lee"}, "labels": [],
                     "created_at": "2026-11-17T10:00:00Z", "closed_at": None},
                    {"number": 9, "title": "PR as issue", "user": {"login": "mira"}, "labels": [],
                     "created_at": "2026-11-18T10:00:00Z", "closed_at": None, "pull_request": {}}]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())


def test_live_fetch_against_a_fake_api(monkeypatch, capsys):
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeGitHub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(wgr, "API", f"http://127.0.0.1:{server.server_address[1]}")
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    try:
        assert wgr.main(["--repos", "me/app", "--week-ending", "2026-11-22"]) == 0
    finally:
        server.shutdown()
    out = capsys.readouterr().out
    assert "| me/app | 1 | 1 | 1 | 1 | 0 |" in out  # the pull request isn't counted as an issue
    assert all(auth == "Bearer test-token" for _, auth in FakeGitHub.seen)
    assert any("since=2026-11-16T00%3A00%3A00Z" in path for path, _ in FakeGitHub.seen)
