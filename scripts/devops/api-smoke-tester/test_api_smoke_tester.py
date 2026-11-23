import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import api_smoke_tester as ast_
import pytest


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, code, payload, content_type="application/json"):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/slow":
            time.sleep(0.2)
            self.send(200, {"ok": True})
        elif self.path == "/users/1":
            self.send(200, {"id": 1, "name": "Ada", "tags": ["a", "b"], "meta": {"n": 5}})
        elif self.path == "/text":
            self.send(200, b"hello plain world", "text/plain")
        elif self.path == "/secure":
            self.send(200, {"token": self.headers.get("Authorization")})
        else:
            self.send(404, {"error": "missing"})

    def do_POST(self):
        size = int(self.headers.get("Content-Length", 0))
        self.send(201, {"echo": json.loads(self.rfile.read(size))})


@pytest.fixture
def base():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def spec_of(base, tests, headers=None):
    return {"base_url": base, "headers": headers or {}, "tests": tests}


def run(base, test, headers=None):
    _, tests = ast_.validate_spec(spec_of(base, [test]))
    return ast_.run_test(tests[0], headers or {}, 5)


def test_validate_spec_reports_problems():
    problems, _ = ast_.validate_spec(spec_of("https://x.test", [
        {"name": "a", "path": "/ok"}, {"name": "a", "path": "/dup"},
        {"name": "b", "bogus": 1, "path": "/x"}, {"name": "c", "method": "FETCH", "path": "/x"},
        {"name": "d", "path": "/x", "expect_status": 99},
        {"name": "f", "path": "/x", "max_ms": "fast", "expect_json": [1]}, "nope"]))
    text = "\n".join(problems)
    assert "'a': the name is used twice" in text and "unknown setting 'bogus'" in text
    assert "unknown method 'FETCH'" in text and "expect_status must be a status code" in text
    assert "max_ms must be a number" in text
    no_base = ast_.validate_spec({"tests": [{"name": "e"}]})[0]
    assert no_base == ["'e': needs a 'url', or a 'path' together with a base_url"]
    assert "expect_json must be an object" in text and "test 7: must be an object" in text
    assert ast_.validate_spec({})[0] == ["the file needs a non-empty 'tests' list"]
    assert ast_.validate_spec({"tests": []})[1] == []


def test_dig_dotted_paths():
    data = {"a": {"b": [10, {"c": "x"}]}}
    assert ast_.dig(data, "a.b.1.c") == (True, "x") and ast_.dig(data, "a.b.0") == (True, 10)
    assert ast_.dig(data, "a.z")[0] is False and ast_.dig(data, "a.b.9")[0] is False


def test_passing_checks(base):
    failures, status, ms = run(base, {"path": "/users/1", "expect_json": {
        "id": 1, "name": "Ada", "meta.n": 5, "tags.1": "b", "tags": "*"},
        "expect_header": {"content-type": "JSON"}, "max_ms": 2000})
    assert failures == [] and status == 200 and ms >= 0


def test_each_kind_of_failure(base):
    failures, _, _ = run(base, {"path": "/users/1", "expect_status": 201,
                                "expect_json": {"name": "Bob", "nope": "*"},
                                "expect_contains": "zzz", "expect_header": {"x-id": "1"}})
    text = "\n".join(failures)
    assert "status 200, expected 201" in text and "'name' is 'Ada', expected 'Bob'" in text
    assert "field 'nope' is missing" in text and "does not contain 'zzz'" in text
    assert "header x-id is None" in text
    assert "took" in run(base, {"path": "/slow", "max_ms": 50})[0][0]
    assert run(base, {"path": "/text", "expect_json": {"a": 1}})[0] == ["body is not JSON"]


def test_post_with_body_and_expected_404(base):
    failures, status, _ = run(base, {"method": "POST", "path": "/x", "body": {"n": 1},
                                     "expect_status": 201, "expect_json": {"echo.n": 1}})
    assert failures == [] and status == 201
    assert run(base, {"path": "/nothing", "expect_status": 404})[0] == []


def test_headers_use_the_environment(base, monkeypatch):
    monkeypatch.setenv("SMOKE_TOKEN", "abc")
    failures, _, _ = run(base, {"path": "/secure", "expect_json": {"token": "Bearer abc"}},
                         {"Authorization": "Bearer ${SMOKE_TOKEN}"})
    assert failures == []
    monkeypatch.delenv("SMOKE_TOKEN")
    failures, status, _ = run(base, {"path": "/secure"}, {"Authorization": "Bearer ${SMOKE_TOKEN}"})
    assert "SMOKE_TOKEN" in failures[0] and status == 0


def test_connection_errors_become_failures():
    failures, status, _ = run("http://127.0.0.1:9", {"path": "/"})
    assert failures[0].startswith("request failed") and status == 0


def test_cli_validate_run_only_and_fail_fast(base, tmp_path, capsys):
    path = tmp_path / "t.json"
    path.write_text(json.dumps(spec_of("https://placeholder.test", [
        {"name": "user", "path": "/users/1", "expect_json": {"id": 1}},
        {"name": "bad", "path": "/users/1", "expect_status": 500},
        {"name": "text", "path": "/text", "expect_contains": "plain"}])))
    assert ast_.main([str(path), "--validate"]) == 0
    out = capsys.readouterr().out
    assert "3 test(s) look valid. No requests were made." in out and "[json]" in out
    assert ast_.main([str(path), "--base-url", base]) == 1
    out = capsys.readouterr().out
    assert "PASS  GET    user" in out and "FAIL  GET    bad" in out and "2 passed, 1 failed." in out
    assert ast_.main([str(path), "--base-url", base, "--fail-fast"]) == 1
    assert "text" not in capsys.readouterr().out.split("FAIL")[1]
    assert ast_.main([str(path), "--base-url", base, "--only", "user"]) == 0
    assert ast_.main([str(path), "--only", "zzz"]) == 1


def test_cli_bad_files(tmp_path, capsys):
    broken = tmp_path / "b.json"
    broken.write_text("{nope")
    assert ast_.main([str(broken)]) == 1
    assert "Can't read" in capsys.readouterr().err
    empty = tmp_path / "e.json"
    empty.write_text("{}")
    assert ast_.main([str(empty)]) == 1
    assert "PROBLEM" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        ast_.main([str(tmp_path / "none.json")])
