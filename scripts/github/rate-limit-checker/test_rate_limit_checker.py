import json
import threading
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import rate_limit_checker as rlc

RESET = int(datetime(2026, 11, 9, 12, 0, tzinfo=UTC).timestamp())
NOW = datetime(2026, 11, 9, 11, 18, 30, tzinfo=UTC).timestamp()
DATA = {"resources": {
    "core": {"limit": 5000, "used": 4821, "remaining": 179, "reset": RESET},
    "search": {"limit": 30, "remaining": 26, "reset": RESET - 3000},
    "graphql": {"limit": 5000, "used": 0, "remaining": 5000, "reset": RESET + 3000},
    "empty": {"limit": 0, "remaining": 0, "reset": RESET}}}


@pytest.mark.parametrize("seconds,text", [
    (-5, "already reset"), (0, "already reset"), (42, "in 42s"), (125, "in 2m 05s"),
    (3600, "in 1h 00m"), (7500, "in 2h 05m")])
def test_describe_wait(seconds, text):
    assert rlc.describe_wait(seconds) == text


def test_summarize_skips_unused_resources_and_derives_used():
    rows = rlc.summarize(DATA, NOW)
    assert [r[0] for r in rows] == ["core", "graphql", "search"]
    core, graphql, search = rows
    assert core[1:4] == (4821, 5000, 179) and round(core[4], 1) == 3.6 and core[6] == "in 41m 30s"
    assert search[1] == 4 and search[6] == "already reset"
    assert graphql[6] == "in 1h 31m"


def test_summarize_handles_junk():
    assert rlc.summarize({}, NOW) == [] and rlc.summarize({"resources": None}, NOW) == []


def test_cli_flags_low_limits(tmp_path, capsys):
    f = tmp_path / "rate.json"
    f.write_text(json.dumps(DATA))
    assert rlc.main(["--from-file", str(f), "--now", "2026-11-09T11:18:30"]) == 1
    out = capsys.readouterr().out
    assert "core" in out and "179 of 5,000" in out and "<-- LOW" in out
    assert out.count("<-- LOW") == 1 and "resets 12:00 UTC in 41m 30s" in out
    assert rlc.main(["--from-file", str(f), "--warn-below", "1"]) == 0


def test_bad_files(tmp_path, capsys):
    f = tmp_path / "rate.json"
    f.write_text('{"message": "Bad credentials"}')
    assert rlc.main(["--from-file", str(f)]) == 1
    f.write_text("not json")
    assert rlc.main(["--from-file", str(f)]) == 1
    with pytest.raises(SystemExit):
        rlc.main(["--from-file", str(f), "--now", "yesterday"])


class Handler(BaseHTTPRequestHandler):
    auth = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        Handler.auth.append(self.headers.get("Authorization"))
        if self.headers.get("Authorization") == "Bearer bad":
            self.send_response(401)
            self.end_headers()
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(DATA).encode())


@pytest.fixture
def server(monkeypatch):
    Handler.auth = []
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    monkeypatch.setattr(rlc, "API", f"http://127.0.0.1:{httpd.server_address[1]}")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    yield httpd
    httpd.shutdown()


def test_live_check_says_whether_a_token_was_used(server, monkeypatch, capsys):
    assert rlc.main(["--warn-below", "1", "--now", "2026-11-09T11:18:30"]) == 0
    assert "No token set" in capsys.readouterr().out
    monkeypatch.setenv("GITHUB_TOKEN", "good")
    assert rlc.main(["--warn-below", "1"]) == 0
    assert "Using a token." in capsys.readouterr().out and Handler.auth[-1] == "Bearer good"


def test_live_bad_token(server, monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_TOKEN", "bad")
    assert rlc.main([]) == 1
    assert "bad token" in capsys.readouterr().err
