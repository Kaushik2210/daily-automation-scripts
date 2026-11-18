import csv
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import health_check_poller as hcp
import pytest


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/slow":
            time.sleep(0.25)
        code = {"/fail": 503, "/created": 201}.get(self.path, 200)
        self.send_response(code)
        self.end_headers()
        self.wfile.write(b"status: healthy")


@pytest.fixture
def base():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_matches():
    assert hcp.matches(200, "2xx") and hcp.matches(204, "204") and not hcp.matches(503, "2xx")
    assert hcp.matches(404, "4XX") and not hcp.matches(201, "200")


def test_check_success_failure_and_content(base):
    good = hcp.check(f"{base}/ok", 3, "2xx", None)
    assert (good["status"], good["ok"], good["error"]) == (200, "yes", "")
    bad = hcp.check(f"{base}/fail", 3, "2xx", None)
    assert (bad["status"], bad["ok"], bad["error"]) == (503, "no", "HTTP 503")
    assert hcp.check(f"{base}/created", 3, "200", None)["error"] == "status 201, expected 200"
    assert hcp.check(f"{base}/ok", 3, "2xx", "healthy")["ok"] == "yes"
    missing = hcp.check(f"{base}/ok", 3, "2xx", "all good")
    assert missing["ok"] == "no" and "does not contain" in missing["error"]


def test_connection_failure_is_reported_not_raised():
    result = hcp.check("http://127.0.0.1:9/", 1, "2xx", None)
    assert result["ok"] == "no" and result["status"] == 0 and result["ms"] == ""
    assert result["error"]


def test_summarise_states():
    rows = [{"url": "a", "ok": "yes", "ms": "50", "error": "", "status": "200"},
            {"url": "a", "ok": "yes", "ms": "2000", "error": "", "status": "200"},
            {"url": "b", "ok": "yes", "ms": "10", "error": "", "status": "200"},
            {"url": "b", "ok": "no", "ms": "10", "error": "HTTP 500", "status": "500"},
            {"url": "c", "ok": "no", "ms": "", "error": "refused", "status": "0"}]
    stats = hcp.summarise(rows, 1000)
    assert [stats[u]["state"] for u in "abc"] == ["SLOW", "DEGRADED", "DOWN"]
    assert stats["b"]["last_error"] == "HTTP 500" and stats["a"]["times"] == [50, 2000]


def test_cli_polls_logs_and_summarises(base, tmp_path, capsys):
    log = tmp_path / "log.csv"
    args = [f"{base}/ok", f"{base}/fail", "--count", "2", "--interval", "0", "--csv", str(log)]
    assert hcp.main(args) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out and "UP       " in out and "DOWN" in out
    assert f"{base}/ok  2/2 ok (100%)" in out
    rows = list(csv.DictReader(log.open(encoding="utf-8")))
    assert len(rows) == 4 and set(rows[0]) == set(hcp.FIELDS)
    hcp.main([f"{base}/ok", "--count", "1", "--csv", str(log)])  # appends without a new header
    assert len(list(csv.DictReader(log.open(encoding="utf-8")))) == 5
    capsys.readouterr()
    assert hcp.main(["--summarise", str(log)]) == 1
    assert "Summary:" in capsys.readouterr().out
    assert hcp.main([f"{base}/ok", "--count", "1", "--contains", "healthy"]) == 0


def test_cli_errors(tmp_path):
    with pytest.raises(SystemExit):
        hcp.main([])
    with pytest.raises(SystemExit):
        hcp.main(["--summarise", str(tmp_path / "none.csv")])
    with pytest.raises(SystemExit):
        hcp.main(["http://x", "--count", "0"])
