import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import contributor_leaderboard as cl
import pytest

ENTRIES = [{"login": "mira", "contributions": 30}, {"login": "sam", "contributions": 60},
           {"login": "dependabot[bot]", "contributions": 10, "type": "Bot"},
           {"login": "Zed", "contributions": 30}, {"name": "Old Contributor", "email": "o@x.test",
                                                    "type": "Anonymous", "contributions": 5},
           {"contributions": 1}]


def test_is_bot():
    assert cl.is_bot({"login": "x[bot]"}) and cl.is_bot({"type": "Bot"})
    assert not cl.is_bot({"login": "sam"}) and not cl.is_bot({})


def test_rank_orders_by_commits_then_name_and_handles_anonymous():
    rows = cl.rank(ENTRIES)
    assert rows[:4] == [("sam", 60), ("mira", 30), ("Zed", 30), ("dependabot[bot]", 10)]
    assert ("Old Contributor", 5) in rows and ("(anonymous)", 1) in rows
    assert ("dependabot[bot]", 10) not in cl.rank(ENTRIES, exclude_bots=True)


def test_render_shares_bars_and_summary():
    text = cl.render([("sam", 60), ("mira", 30), ("tom", 10)], top=2, width=20)
    lines = text.splitlines()
    assert lines[0].startswith("  1. sam ") and "60.0%" in lines[0] and lines[0].count("#") == 20
    assert lines[1].count("#") == 10
    assert lines[-1] == "3 contributor(s), 100 commits. The top 2 wrote 90%."


def test_cli_from_file(tmp_path, capsys):
    f = tmp_path / "c.json"
    f.write_text(json.dumps(ENTRIES))
    assert cl.main(["--from-file", str(f), "--top", "3", "--exclude-bots"]) == 0
    out = capsys.readouterr().out
    assert "sam" in out and "dependabot" not in out and "Old Contributor" not in out
    f.write_text("[]")
    assert cl.main(["--from-file", str(f)]) == 1
    f.write_text('[{"login": "a", "contributions": 0}]')
    assert cl.main(["--from-file", str(f)]) == 1
    f.write_text('{"message": "Not Found"}')
    assert cl.main(["--from-file", str(f)]) == 1


def test_argument_errors():
    for bad in ([], ["notarepo"], ["o/r", "--top", "0"]):
        with pytest.raises(SystemExit):
            cl.main(bad)


class Handler(BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        Handler.seen.append(self.path)
        host = f"http://127.0.0.1:{self.server.server_address[1]}"
        link = ""
        if self.path.startswith("/repos/o/r/contributors") and "page=2" not in self.path:
            body, link = ENTRIES[:3], f'<{host}/repos/o/r/contributors?page=2>; rel="next"'
        elif "page=2" in self.path:
            body = ENTRIES[3:]
        elif self.path.startswith("/repos/o/empty/contributors"):
            self.send_response(204)  # GitHub answers an empty repository with no body at all
            self.end_headers()
            return
        else:
            self.send_response(403)
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
    monkeypatch.setattr(cl, "API", f"http://127.0.0.1:{httpd.server_address[1]}")
    yield httpd
    httpd.shutdown()


def test_live_paging_empty_repo_and_denied(server, capsys):
    assert cl.main(["o/r", "--top", "2"]) == 0
    out = capsys.readouterr().out
    assert "sam" in out and "6 contributor(s), 136 commits" in out
    assert "anon=1" in Handler.seen[0] and len(Handler.seen) == 2
    assert cl.main(["o/empty"]) == 1
    assert "No contributors found" in capsys.readouterr().out
    assert cl.main(["o/huge"]) == 1
    assert "403" in capsys.readouterr().err
