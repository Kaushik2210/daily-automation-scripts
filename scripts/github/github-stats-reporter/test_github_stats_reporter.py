import json
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import github_stats_reporter as gsr
import pytest

TODAY = date(2026, 11, 9)


def repo(name, stars, lang="Python", pushed="2026-11-05T10:00:00Z", **extra):
    return {"name": name, "full_name": f"me/{name}", "stargazers_count": stars,
            "forks_count": stars // 10, "open_issues_count": 1, "language": lang,
            "pushed_at": pushed, "description": f"{name} repo", **extra}


REPOS = [repo("a", 100), repo("b", 300, "Go"), repo("old", 5, pushed="2025-01-01T00:00:00Z"),
         repo("fork", 999, fork=True)]


def test_days_since_and_ago():
    assert gsr.days_since("2026-11-05T10:00:00Z", TODAY) == 4
    assert gsr.days_since(None, TODAY) is None and gsr.days_since("garbage", TODAY) is None
    assert [gsr.ago(d) for d in (None, 0, 12, 200)] == [
        "unknown", "today", "12 day(s) ago", "6 month(s) ago"]


def test_repo_report_shows_flags_and_missing_values():
    text = gsr.repo_report(repo("x", 1234, archived=True, license={"spdx_id": "MIT"}), TODAY)
    assert text.splitlines()[0] == "me/x  [archived]"
    assert "Stars    : 1,234" in text and "License: MIT" in text
    assert "4 day(s) ago" in text
    bare = gsr.repo_report({"name": "n", "pushed_at": None}, TODAY)
    assert "(no description)" in bare and "License: none" in bare and "unknown" in bare


def test_user_report_totals_exclude_forks_by_default():
    text = gsr.user_report(REPOS, TODAY)
    assert text.startswith("3 repositories (+1 forks left out)")
    assert "Stars: 405    Forks: 40    Pushed in the last 30 days: 2" in text
    assert "Python (2), Go (1)" in text
    assert text.index(" b ") < text.index(" a ")  # ranked by stars
    assert "4 repositories" in gsr.user_report(REPOS, TODAY, include_forks=True)


def test_from_file_handles_a_repo_and_a_list(tmp_path, capsys):
    one, many = tmp_path / "repo.json", tmp_path / "repos.json"
    one.write_text(json.dumps(REPOS[0]))
    many.write_text(json.dumps(REPOS))
    assert gsr.main(["--from-file", str(one), "--today", "2026-11-09"]) == 0
    assert capsys.readouterr().out.startswith("me/a")
    assert gsr.main(["--from-file", str(many), "--today", "2026-11-09"]) == 0
    assert "3 repositories" in capsys.readouterr().out
    many.write_text("[]")
    assert gsr.main(["--from-file", str(many)]) == 1


class Handler(BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        Handler.seen.append((self.path, self.headers.get("Authorization")))
        host = f"http://127.0.0.1:{self.server.server_address[1]}"
        if self.path.startswith("/users/me/repos?") and "page=2" not in self.path:
            body, link = json.dumps(REPOS[:2]), f'<{host}/users/me/repos?page=2>; rel="next"'
        elif self.path.startswith("/users/me/repos"):
            body, link = json.dumps(REPOS[2:]), ""
        elif self.path == "/repos/me/a":
            body, link = json.dumps(REPOS[0]), ""
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        if link:
            self.send_header("Link", link)
        self.end_headers()
        self.wfile.write(body.encode())


@pytest.fixture
def server(monkeypatch):
    Handler.seen = []
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    monkeypatch.setattr(gsr, "API", f"http://127.0.0.1:{httpd.server_address[1]}")
    yield httpd
    httpd.shutdown()


def test_live_user_follows_paging_and_sends_the_token(server, monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
    assert gsr.main(["me", "--today", "2026-11-09"]) == 0
    assert "3 repositories" in capsys.readouterr().out
    assert len(Handler.seen) == 2 and all(a == "Bearer secret-token" for _, a in Handler.seen)


def test_live_repo_and_errors(server, monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    assert gsr.main(["me/a", "--today", "2026-11-09"]) == 0
    assert "Stars    : 100" in capsys.readouterr().out
    assert gsr.main(["me/missing"]) == 1
    assert "GitHub said 404 (not found)" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        gsr.main([])


def test_paging_links_to_other_hosts_are_not_followed(monkeypatch):
    class Evil(Handler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Link", '<http://evil.test/next>; rel="next"')
            self.end_headers()
            self.wfile.write(b"[]")

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Evil)
    threading_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    threading_thread.start()
    monkeypatch.setattr(gsr, "API", f"http://127.0.0.1:{httpd.server_address[1]}")
    try:
        assert gsr.api_get("/x", max_pages=3) == []
    finally:
        httpd.shutdown()
