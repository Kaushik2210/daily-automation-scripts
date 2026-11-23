import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import api_recorder as ar
import pytest


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, code, payload, content_type="application/json"):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Set-Cookie", "session=secret")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/text":
            self.reply(200, b"plain words", "text/plain")
        elif self.path == "/missing":
            self.reply(404, {"error": "nope"})
        else:
            self.reply(200, {"path": self.path, "auth": self.headers.get("Authorization")})

    def do_POST(self):
        size = int(self.headers.get("Content-Length", 0))
        self.reply(201, {"echo": json.loads(self.rfile.read(size))})


@pytest.fixture
def base():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def write_spec(tmp_path, base, calls=None):
    spec = {"base_url": base, "headers": {"Authorization": "Bearer ${TEST_TOKEN}"},
            "calls": calls or [{"name": "users", "path": "/users?x=1"},
                               {"name": "create", "method": "post", "path": "/users",
                                "body": {"name": "Zed"}},
                               {"name": "note", "path": "/text"},
                               {"name": "gone", "path": "/missing"}]}
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec))
    return path


def test_expand_and_redact(monkeypatch):
    monkeypatch.setenv("A_VAR", "value")
    missing = set()
    assert ar.expand("x-${A_VAR}-${NOPE_VAR}", missing) == "x-value-${NOPE_VAR}"
    assert missing == {"NOPE_VAR"} and ar.expand(5, missing) == 5
    assert ar.redact({"Authorization": "Bearer x", "Content-Type": "json", "Cookie": "a=b"}) == {
        "authorization": "<redacted>", "content-type": "json", "cookie": "<redacted>"}


def test_build_calls_merges_headers_and_validates(tmp_path):
    spec = {"base_url": "https://api.test/", "headers": {"Accept": "a"},
            "calls": [{"name": "one", "path": "/x", "headers": {"Accept": "b", "X": "1"}},
                      {"url": "https://other.test/y", "method": "delete"}]}
    calls, _ = ar.build_calls(spec)
    assert calls[0]["url"] == "https://api.test/x" and calls[0]["headers"] == {"Accept": "b",
                                                                                "X": "1"}
    assert calls[1]["name"] == "call-2" and calls[1]["method"] == "DELETE"
    for bad in ({"calls": [{"name": "a b", "url": "https://x"}]},
                {"calls": [{"name": "a", "url": "https://x"}, {"name": "a", "url": "https://y"}]},
                {"calls": [{"name": "a", "path": "/x"}]}):
        with pytest.raises(ValueError):
            ar.build_calls(bad)


def test_plan_makes_no_request_and_writes_nothing(tmp_path, base, capsys):
    spec = write_spec(tmp_path, base)
    assert ar.main([str(spec), "-o", str(tmp_path / "fx")]) == 0
    out = capsys.readouterr().out
    assert "users" in out and "[new]" in out and "Plan only: 4 call(s)" in out
    assert "TEST_TOKEN" in out and not (tmp_path / "fx").exists()


def test_apply_records_fixtures_with_redaction(tmp_path, base, monkeypatch, capsys):
    monkeypatch.setenv("TEST_TOKEN", "s3cret")
    spec, out = write_spec(tmp_path, base), tmp_path / "fx"
    assert ar.main([str(spec), "-o", str(out), "--apply"]) == 0
    users = json.loads((out / "users.json").read_text())
    assert users["request"]["headers"]["authorization"] == "<redacted>"
    assert users["response"]["status"] == 200
    assert users["response"]["json"]["auth"] == "Bearer s3cret"
    assert "set-cookie" in users["response"]["headers"] and users["response"]["headers"][
        "set-cookie"] == "<redacted>"
    assert "s3cret" not in json.dumps(users["request"]) + json.dumps(users["response"]["headers"])
    created = json.loads((out / "create.json").read_text())
    assert created["request"]["body"] == {"name": "Zed"} and created["response"]["status"] == 201
    assert json.loads((out / "note.json").read_text())["response"]["text"] == "plain words"
    assert json.loads((out / "gone.json").read_text())["response"]["status"] == 404
    assert "4 recorded, 0 kept, 0 failed." in capsys.readouterr().out


def test_existing_fixtures_are_kept_unless_refreshed(tmp_path, base, monkeypatch, capsys):
    monkeypatch.setenv("TEST_TOKEN", "t")
    spec, out = write_spec(tmp_path, base), tmp_path / "fx"
    out.mkdir()
    (out / "users.json").write_text('{"old": true}')
    ar.main([str(spec), "-o", str(out), "--apply", "--only", "users"])
    assert (out / "users.json").read_text() == '{"old": true}'
    assert "1 kept" in capsys.readouterr().out
    ar.main([str(spec), "-o", str(out), "--apply", "--only", "users", "--refresh"])
    assert "request" in json.loads((out / "users.json").read_text())


def test_apply_needs_the_environment_and_reports_connection_errors(tmp_path, base, monkeypatch,
                                                                    capsys):
    monkeypatch.delenv("TEST_TOKEN", raising=False)
    spec = write_spec(tmp_path, base)
    assert ar.main([str(spec), "-o", str(tmp_path / "fx"), "--apply"]) == 1
    assert "TEST_TOKEN" in capsys.readouterr().err
    dead = write_spec(tmp_path, "http://127.0.0.1:9", [{"name": "x", "path": "/"}])
    monkeypatch.setenv("TEST_TOKEN", "t")
    assert ar.main([str(dead), "-o", str(tmp_path / "fx2"), "--apply", "--timeout", "1"]) == 1
    assert "FAILED" in capsys.readouterr().out


def test_list_and_errors(tmp_path, capsys):
    out = tmp_path / "fx"
    out.mkdir()
    (out / "a.json").write_text(json.dumps({"request": {"method": "GET", "url": "https://x/a"},
                                            "response": {"status": 200, "ms": 12, "json": {}},
                                            "recorded_at": "2026-11-20T10:00:00"}))
    (out / "bad.json").write_text("{nope")
    assert ar.main(["--list", "-o", str(out)]) == 0
    text = capsys.readouterr().out
    assert "a" in text and "GET" in text and "unreadable fixture" in text and "2 fixture(s)" in text
    assert ar.main(["--list", "-o", str(tmp_path / "none")]) == 1
    with pytest.raises(SystemExit):
        ar.main([])
    broken = tmp_path / "b.json"
    broken.write_text("{}")
    assert ar.main([str(broken)]) == 1
    assert "'calls' list" in capsys.readouterr().err
    assert ar.main([str(write_spec(tmp_path, "https://x.test")), "--only", "zzz"]) == 1
