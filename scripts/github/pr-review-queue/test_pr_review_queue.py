import json
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pr_review_queue as prq
import pytest

TODAY = date(2026, 11, 9)


def pr(number, repo, created, draft=False, **extra):
    return {"number": number, "title": f"PR {number}", "user": {"login": "ann"}, "comments": 1,
            "created_at": created, "draft": draft, "html_url": f"https://github.com/o/{repo}/pull/{number}",
            "repository_url": f"https://api.github.com/repos/o/{repo}", **extra}


ITEMS = [pr(5, "web", "2026-11-08T10:00:00Z"), pr(2, "api", "2026-10-20T09:00:00Z"),
         pr(9, "api", "2026-11-01T09:00:00Z", draft=True)]


def test_waiting_days_handles_bad_dates():
    assert prq.waiting_days({"created_at": "2026-11-01T09:00:00Z"}, TODAY) == 8
    assert prq.waiting_days({}, TODAY) == 0 and prq.waiting_days({"created_at": "x"}, TODAY) == 0


def test_queue_orders_oldest_first_and_hides_drafts():
    rows = prq.queue(ITEMS, TODAY)
    assert [(r["repo"], r["number"], r["days"]) for r in rows] == [
        ("o/api", 2, 20), ("o/web", 5, 1)]
    with_drafts = prq.queue(ITEMS, TODAY, include_drafts=True)
    assert [r["number"] for r in with_drafts] == [2, 9, 5] and with_drafts[1]["draft"]


def test_cli_from_file_marks_slow_reviews(tmp_path, capsys):
    f = tmp_path / "search.json"
    f.write_text(json.dumps({"total_count": 3, "items": ITEMS}))
    assert prq.main(["--from-file", str(f), "--today", "2026-11-09"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("2 pull request(s) waiting for review:")
    assert "20d  o/api#2  PR 2  <-- waiting a while" in out
    assert "o/web#5  PR 5\n" in out
    assert prq.main(["--from-file", str(f), "--today", "2026-11-09", "--include-drafts"]) == 0
    assert "[draft]" in capsys.readouterr().out


def test_empty_and_malformed_files(tmp_path, capsys):
    f = tmp_path / "s.json"
    f.write_text('{"items": []}')
    assert prq.main(["--from-file", str(f)]) == 0
    assert "Nothing is waiting" in capsys.readouterr().out
    f.write_text('{"message": "Bad credentials"}')
    assert prq.main(["--from-file", str(f)]) == 1
    f.write_text("[]")
    assert prq.main(["--from-file", str(f)]) == 0  # a bare list of items also works


class Handler(BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        Handler.seen.append((self.path, self.headers.get("Authorization")))
        if "review-requested%3Abroken" in self.path:
            self.send_response(422)
            self.end_headers()
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"items": ITEMS[:2]}).encode())


@pytest.fixture
def server(monkeypatch):
    Handler.seen = []
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    monkeypatch.setattr(prq, "API", f"http://127.0.0.1:{httpd.server_address[1]}")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    yield httpd
    httpd.shutdown()


def test_live_search_asks_for_my_review_requests(server, monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    assert prq.main(["--org", "o", "--today", "2026-11-09"]) == 0
    path, auth = Handler.seen[0]
    assert "review-requested%3A%40me" in path and "org%3Ao" in path and auth == "Bearer tok"
    assert "o/api#2" in capsys.readouterr().out


def test_at_me_needs_a_token_but_a_named_user_does_not(server, capsys):
    assert prq.main([]) == 1
    assert "GITHUB_TOKEN" in capsys.readouterr().err
    assert prq.main(["--user", "ann"]) == 0
    assert Handler.seen[0][1] is None
    assert prq.main(["--user", "broken"]) == 1
    assert "422" in capsys.readouterr().err
