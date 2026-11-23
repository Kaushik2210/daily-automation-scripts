import json
import threading
import urllib.error
import urllib.request

import mock_server as ms
import pytest

DEFINITION = {"port": 8123, "routes": [
    {"method": "GET", "path": "/users", "body": {"users": [{"id": 1}]}},
    {"method": "GET", "path": "/users/{id}", "body": {"id": "{id}", "name": "User {id}",
                                                         "q": "{query.verbose}"}},
    {"method": "POST", "path": "/users", "status": 201, "body": {"created": True},
     "headers": {"Location": "/users/{id}"}},
    {"method": "GET", "path": "/text", "body": "plain {x}"},
    {"method": "GET", "path": "/empty", "status": 204},
    {"method": "*", "path": "/any", "body": {"any": True}},
    {"method": "GET", "path": "/slow", "delay_ms": 250, "body": {"ok": True}}]}


def routes():
    problems, normalised = ms.validate(DEFINITION)
    assert problems == []
    return normalised


def test_validate_reports_problems():
    problems, _ = ms.validate({"routes": [
        {"method": "FETCH", "path": "/a"}, {"path": "no-slash"}, {"path": "/b", "status": "ok"},
        {"path": "/c", "delay_ms": -5}, {"path": "/d", "headers": []},
        {"path": "/e"}, {"path": "/e"}, "nope"]})
    text = "\n".join(problems)
    assert "unknown method" in text and "must start with /" in text
    assert "status must be a code" in text and "delay_ms must be a positive number" in text
    assert "headers must be an object" in text and "defined twice" in text
    assert "route 8: must be an object" in text
    assert ms.validate({})[0] == ["the file needs a 'routes' list"]


def test_find_route_params_methods_and_wildcards():
    found = routes()
    route, params = ms.find_route(found, "get", "/users/42")
    assert route["path"] == "/users/{id}" and params == {"id": "42"}
    assert ms.find_route(found, "GET", "/users/42/")[1] == {"id": "42"}
    assert ms.find_route(found, "POST", "/users")[0]["status"] == 201
    assert ms.find_route(found, "DELETE", "/any")[0]["path"] == "/any"
    assert ms.find_route(found, "DELETE", "/users")[0] is None
    assert ms.find_route(found, "GET", "/users/1/extra")[0] is None


def test_fill_placeholders_recursively():
    assert ms.fill({"a": ["x {id}", 5], "b": {"c": "{missing}"}}, {"id": 7}) == {
        "a": ["x 7", 5], "b": {"c": "{missing}"}}


def test_build_response_json_text_empty_and_unknown():
    found = routes()
    status, headers, body, delay = ms.build_response(found, "GET", "/users/9?verbose=yes")
    assert status == 200 and headers["Content-Type"] == "application/json" and delay == 0
    assert json.loads(body) == {"id": "9", "name": "User 9", "q": "yes"}
    status, headers, body, _ = ms.build_response(found, "POST", "/users")
    assert status == 201 and headers["Location"] == "/users/{id}"
    status, headers, body, _ = ms.build_response(found, "GET", "/text")
    assert body == b"plain {x}" and headers["Content-Type"].startswith("text/plain")
    assert ms.build_response(found, "GET", "/empty")[2] == b""
    assert ms.build_response(found, "GET", "/slow")[3] == 0.25
    status, _, body, _ = ms.build_response(found, "GET", "/nope")
    error = json.loads(body)
    assert status == 404 and error["error"] == "no mock for GET /nope" and "GET /users" in (
        error["routes"])


@pytest.fixture
def server():
    log, naps = [], []
    httpd = ms.make_server("127.0.0.1", 0, routes(), on_request=log.append, sleep=naps.append)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}", log, naps
    httpd.shutdown()
    httpd.server_close()


def call(url, method="GET", data=None):
    request = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers), err.read()


def test_real_server_responses_cors_and_delay(server):
    base, log, naps = server
    status, headers, body = call(f"{base}/users/5")
    assert status == 200 and json.loads(body)["name"] == "User 5"
    assert headers["Access-Control-Allow-Origin"] == "*"
    assert call(f"{base}/users", "POST", b"{}")[0] == 201
    assert call(f"{base}/missing")[0] == 404
    status, headers, _ = call(f"{base}/users", "OPTIONS")
    assert status == 204 and "POST" in headers["Access-Control-Allow-Methods"]
    call(f"{base}/slow")
    assert naps == [0.25] and any("GET    /users/5" in line for line in log)
    assert any("(after 0.25s)" in line for line in log)


def test_cli_check_simulate_and_errors(tmp_path, capsys):
    path = tmp_path / "mock.json"
    path.write_text(json.dumps(DEFINITION))
    assert ms.main(["check", str(path)]) == 0
    out = capsys.readouterr().out
    assert "GET    /users/{id}" in out and "(delay 250 ms)" in out
    assert "7 route(s) look valid; the server would listen on port 8123." in out
    assert ms.main(["simulate", str(path), "GET /users/3?verbose=1"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("HTTP 200") and "Content-Type: application/json" in out
    assert '"name": "User 3"' in out
    assert ms.main(["simulate", str(path), "GET /nothing"]) == 1
    assert ms.main(["simulate", str(path), "GET /slow"]) == 0
    assert "the real server would wait 0.25s" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        ms.main(["simulate", str(path), "nonsense"])
    bad = tmp_path / "bad.json"
    bad.write_text('{"routes": [{"method": "X", "path": "/a"}]}')
    assert ms.main(["check", str(bad)]) == 1
    assert "PROBLEM" in capsys.readouterr().out
    bad.write_text("{nope")
    assert ms.main(["check", str(bad)]) == 1


def test_serve_stops_after_max_requests(tmp_path, capsys):
    path = tmp_path / "mock.json"
    path.write_text(json.dumps({"routes": [{"path": "/ping", "body": {"pong": True}}]}))
    done = []

    def run():
        done.append(ms.main(["serve", str(path), "--port", "0", "--max-requests", "1"]))

    # port 0 picks a free port, but the client needs to know it: probe the output instead
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    deadline = threading.Event()
    port = None
    for _ in range(100):
        text = capsys.readouterr().out
        if "http://127.0.0.1:" in text:
            port = int(text.split("http://127.0.0.1:")[1].split("/")[0])
            break
        deadline.wait(0.05)
    assert port
    assert call(f"http://127.0.0.1:{port}/ping")[0] == 200
    thread.join(timeout=5)
    assert done == [0]
