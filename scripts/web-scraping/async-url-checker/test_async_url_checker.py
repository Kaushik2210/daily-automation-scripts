import asyncio
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import async_url_checker as auc
import pytest


class State:
    lock = threading.Lock()
    active = 0
    peak = 0
    flaky_calls = 0


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self, send_body):
        path = self.path
        with State.lock:
            State.active += 1
            State.peak = max(State.peak, State.active)
        try:
            if path.startswith("/slow"):
                time.sleep(0.15)
            if path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "/ok")
                self.end_headers()
                return
            if path == "/nohead" and not send_body:
                self.send_response(405)
                self.end_headers()
                return
            if path == "/flaky":
                with State.lock:
                    State.flaky_calls += 1
                    first = State.flaky_calls == 1
                code = 503 if first else 200
            else:
                code = 404 if path == "/missing" else 200
            self.send_response(code)
            self.end_headers()
            if send_body:
                self.wfile.write(b"ok")
        finally:
            with State.lock:
                State.active -= 1

    def do_GET(self):
        self.respond(True)

    def do_HEAD(self):
        self.respond(False)


@pytest.fixture
def server():
    State.active = State.peak = State.flaky_calls = 0
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def check(urls, **kwargs):
    options = {"concurrency": 10, "per_host": 10, "timeout": 5, "retries": 0, "method": "HEAD",
               "follow": True}
    options.update(kwargs)
    return asyncio.run(auc.check_all(urls, **options))


def test_read_urls_dedupes_and_flags_invalid(tmp_path):
    listing = tmp_path / "u.txt"
    listing.write_text("# c\nhttps://a.com\nnot a url\nhttps://a.com\nftp://x.org\n")
    urls, invalid, duplicates = auc.read_urls([str(listing), "https://b.com"])
    assert urls == ["https://a.com", "https://b.com"] and duplicates == 1
    assert invalid == ["not a url", "ftp://x.org"]


def test_statuses_and_order_are_kept(server):
    urls = [f"{server}/ok", f"{server}/missing", f"{server}/redirect"]
    rows = check(urls)
    assert [r["url"] for r in rows] == urls
    assert [r["status"] for r in rows] == [200, 404, 200]
    assert rows[1]["error"] == "HTTP 404" and rows[2]["final_url"] == f"{server}/ok"
    assert [auc.classify(r) for r in rows] == ["ok", "client error", "redirect"]


def test_no_follow_reports_the_redirect(server):
    (row,) = check([f"{server}/redirect"], follow=False)
    assert row["status"] == 302 and auc.classify(row) == "redirect"


def test_head_falls_back_to_get_and_retries_help(server):
    assert check([f"{server}/nohead"])[0]["status"] == 200
    assert check([f"{server}/flaky"], retries=0)[0]["status"] == 503
    State.flaky_calls = 0
    assert check([f"{server}/flaky"], retries=1)[0]["status"] == 200


def test_concurrency_limit_is_respected(server):
    urls = [f"{server}/slow{i}" for i in range(12)]
    check(urls, concurrency=3, per_host=3)
    assert 2 <= State.peak <= 3
    State.peak = 0
    check(urls, concurrency=12, per_host=12)
    assert State.peak > 3


def test_per_host_limit(server):
    State.peak = 0
    check([f"{server}/slow{i}" for i in range(8)], concurrency=8, per_host=2)
    assert State.peak <= 2


def test_connection_errors_are_results_not_crashes():
    (row,) = check(["http://127.0.0.1:9/"], timeout=1)
    assert row["status"] == 0 and row["error"] and auc.classify(row) == "failed"


def test_summarise_report(tmp_path, capsys):
    saved = tmp_path / "r.csv"
    saved.write_text("url,status,ms,final_url,error\nhttps://a/,200,50,https://a/,\n"
                     "https://b/,404,60,https://b/,HTTP 404\nhttps://c/,0,,,refused\n"
                     "https://d/,200,3000,https://d/,\n")
    assert auc.main(["--summarise", str(saved)]) == 1
    out = capsys.readouterr().out
    assert "CLIENT ERROR  404" in out and "FAILED" in out and "(slow)" in out
    assert "4 URL(s): 2 ok, 1 client error, 1 failed." in out
    assert auc.main(["--summarise", str(saved), "--only-problems"]) == 1
    assert "https://a/" not in capsys.readouterr().out


def test_cli_plan_and_live_run_with_csv(server, tmp_path, capsys):
    assert auc.main([f"{server}/ok", f"{server}/ok", "nope", "--plan"]) == 0
    out = capsys.readouterr().out
    assert "1 URL(s) on 1 site(s); 1 duplicate(s) removed, 1 invalid." in out
    assert "No requests were made" in out
    target = tmp_path / "out.csv"
    assert auc.main([f"{server}/ok", f"{server}/missing", "--csv", str(target)]) == 1
    assert target.read_text().splitlines()[0] == "url,status,ms,final_url,error"
    with pytest.raises(SystemExit):
        auc.main([f"{server}/ok", "--csv", str(target)])  # never overwrites
    with pytest.raises(SystemExit):
        auc.main([])
