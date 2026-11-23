import json
import threading
import urllib.error
import urllib.request

import pytest
import webhook_receiver as wr

SECRET = "topsecret"


def post(url, body, headers=None, method="POST"):
    data = body if isinstance(body, bytes) else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as err:
        return err.code, json.load(err)


@pytest.fixture
def running(tmp_path):
    events = []
    log = tmp_path / "log.jsonl"

    def start(**options):
        server = wr.make_server("127.0.0.1", 0, log, on_event=events.append, **options)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        started.append(server)
        return f"http://127.0.0.1:{server.server_address[1]}", log, events

    started = []
    yield start
    for server in started:
        server.shutdown()
        server.server_close()


def test_sign_and_check_signature():
    body = b'{"a": 1}'
    good = wr.sign(SECRET, body)
    assert good.startswith("sha256=") and len(good) == 71
    assert wr.check_signature(SECRET, body, {"x-hub-signature-256": good}) == "valid"
    bare = good.removeprefix("sha256=")  # some services send just the hex digest
    assert wr.check_signature(SECRET, body, {"x-signature": bare}) == "valid"
    assert wr.check_signature(SECRET, body, {"x-hub-signature-256": "sha256=00"}) == "INVALID"
    assert wr.check_signature(SECRET, b"tampered", {"x-hub-signature-256": good}) == "INVALID"
    assert wr.check_signature(SECRET, body, {}) == "none"
    assert wr.check_signature(None, body, {"x-hub-signature-256": good}) == "none"


def test_describe_body():
    assert wr.describe_body(b'{"a": 1}', "application/json") == {"a": 1}
    assert wr.describe_body(b"[1, 2]", "") == [1, 2]
    assert wr.describe_body(b"name=Ada&x=1", "application/x-www-form-urlencoded") == "name=Ada&x=1"
    assert wr.describe_body(b"{broken", "application/json") == "{broken"
    assert wr.describe_body(b"", "") is None


def test_make_entry_redacts_credentials():
    entry = wr.make_entry("POST", "/h", {"Authorization": "Bearer x", "Content-Type": "text/plain",
                                         "Cookie": "a=b"}, b"hi", None)
    assert entry["headers"]["authorization"] == "<redacted>" and entry["headers"]["cookie"] == (
        "<redacted>")
    assert entry["body"] == "hi" and entry["size"] == 2 and entry["method"] == "POST"


def test_server_logs_requests_and_answers(running):
    base, log, events = running()
    status, reply = post(f"{base}/hooks/a", {"hello": "world"})
    assert status == 200 and reply == {"received": True, "signature": "none"}
    status, _ = post(f"{base}/hooks/b", b"", method="GET")
    assert status == 200
    entries = wr.read_log(log)
    assert [e["path"] for e in entries] == ["/hooks/a", "/hooks/b"]
    assert entries[0]["body"] == {"hello": "world"} and entries[1]["body"] is None
    assert len(events) == 2 and entries[0]["responded"] == 200


def test_signatures_checked_and_invalid_can_be_rejected(running):
    base, log, _ = running(secret=SECRET, reject_invalid=True)
    body = json.dumps({"n": 1}).encode()
    ok, reply = post(f"{base}/h", body, {"X-Hub-Signature-256": wr.sign(SECRET, body)})
    assert ok == 200 and reply["signature"] == "valid"
    bad, reply = post(f"{base}/h", body, {"X-Hub-Signature-256": "sha256=deadbeef"})
    assert bad == 401 and reply == {"received": False, "signature": "INVALID"}
    assert [e["signature"] for e in wr.read_log(log)] == ["valid", "INVALID"]


def test_custom_status_and_max_requests(tmp_path):
    log = tmp_path / "l.jsonl"
    server = wr.make_server("127.0.0.1", 0, log, status=202, on_event=lambda e: None,
                            max_requests=2)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    assert post(f"{base}/a", {})[0] == 202
    post(f"{base}/b", {})
    thread.join(timeout=5)
    assert not thread.is_alive()  # the server stopped itself after two requests
    server.server_close()


def test_show_and_verify_cli(tmp_path, capsys):
    log = tmp_path / "log.jsonl"
    rows = [{"time": "2026-11-21T09:00:00", "method": "POST", "path": "/hooks/github",
             "signature": "valid", "size": 20, "body": {"ref": "main"}},
            {"time": "2026-11-21T09:01:00", "method": "POST", "path": "/hooks/stripe",
             "signature": "INVALID", "size": 5, "body": "text body"}]
    log.write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n")
    assert wr.main(["show", str(log)]) == 1
    out = capsys.readouterr().out
    assert "/hooks/github" in out and '{"ref": "main"}' in out and "text body" in out
    assert "2 request(s), 1 with an INVALID signature" in out
    assert wr.main(["show", str(log), "--path", "github"]) == 0
    payload = tmp_path / "p.json"
    payload.write_bytes(b'{"x": 1}')
    sig = wr.sign(SECRET, b'{"x": 1}')
    assert wr.main(["verify", str(payload), "--secret", SECRET, "--signature", sig]) == 0
    assert "Result:   VALID" in capsys.readouterr().out
    assert wr.main(["verify", str(payload), "--secret", "wrong", "--signature", sig]) == 1
    assert "Result:   INVALID" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        wr.main(["verify", str(payload)])
    with pytest.raises(SystemExit):
        wr.main(["show"])


def test_serve_reports_a_busy_port(tmp_path, capsys):
    import socket
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        port = busy.getsockname()[1]
        assert wr.main(["serve", "--port", str(port), "--log", str(tmp_path / "l")]) == 1
    assert "Can't listen" in capsys.readouterr().err
