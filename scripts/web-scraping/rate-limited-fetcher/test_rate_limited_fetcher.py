import random
import threading
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import rate_limited_fetcher as rlf


@pytest.mark.parametrize("value,expected", [
    ("5", 5.0), (" 2.5 ", 2.5), ("", None), (None, None), ("soon", None)])
def test_parse_retry_after_numbers(value, expected):
    assert rlf.parse_retry_after(value) == expected


def test_parse_retry_after_http_date():
    now = datetime(2026, 11, 21, 12, 0, 0, tzinfo=UTC)
    later = (now + timedelta(seconds=90)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    assert rlf.parse_retry_after(later, now) == 90
    assert rlf.parse_retry_after("Mon, 01 Jan 2001 00:00:00 GMT", now) == 0


def test_backoff_grows_is_capped_and_jittered():
    rng = random.Random(1)
    delays = [rlf.backoff_delay(n, 1, 30, 0, rng) for n in range(8)]
    assert delays == [1, 2, 4, 8, 16, 30, 30, 30]
    jittered = {round(rlf.backoff_delay(2, 1, 30, 0.2, random.Random(i)), 3) for i in range(20)}
    assert len(jittered) > 5 and all(3.2 <= d <= 4.8 for d in jittered)


def test_schedule_and_file_names():
    assert rlf.schedule(4, 2) == [0.0, 0.5, 1.0, 1.5]
    assert rlf.file_name("https://x.org/a/report.pdf") == "report.pdf"
    assert rlf.file_name("https://x.org/a/report.pdf?v=2").startswith("report.pdf-")
    assert rlf.file_name("https://x.org/").startswith("-")  # no name: just a short hash


class Fake:
    """A scripted fetch function and a fake clock so no test really waits."""

    def __init__(self, answers):
        self.answers, self.calls, self.now, self.sleeps = answers, [], 0.0, []

    def fetch(self, url, timeout):
        self.calls.append((url, self.now))
        return self.answers.get(url, [(200, {}, b"ok", "")]).pop(0)

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds

    def clock(self):
        return self.now


def run(fake, urls, **options):
    settings = {"rate": 2, "retries": 2, "timeout": 5, "backoff": 1}
    settings.update(options)
    return rlf.fetch_all(urls, fetch=fake.fetch, sleep=fake.sleep, clock=fake.clock,
                         rng=random.Random(0), out=lambda text: None, **settings)


def test_requests_to_one_host_are_spaced_by_the_rate():
    fake = Fake({})
    run(fake, ["https://a.org/1", "https://a.org/2", "https://a.org/3"], rate=2)
    times = [t for _, t in fake.calls]
    assert times == [0.0, 0.5, 1.0]


def test_different_hosts_do_not_wait_for_each_other():
    fake = Fake({})
    run(fake, ["https://a.org/1", "https://b.org/1"], rate=1)
    assert [t for _, t in fake.calls] == [0.0, 0.0]


def test_retry_after_is_obeyed_before_backoff():
    fake = Fake({"https://a.org/x": [(429, {"Retry-After": "7"}, b"", "HTTP 429"),
                                     (200, {}, b"done", "")]})
    (result,) = run(fake, ["https://a.org/x"], rate=100)
    assert result["status"] == 200 and result["attempts"] == 2 and result["body"] == b"done"
    assert 7.0 in fake.sleeps and fake.calls[1][1] >= 7


def test_backoff_when_there_is_no_retry_after_and_final_failure():
    fake = Fake({"https://a.org/x": [(503, {}, b"", "HTTP 503")] * 3})
    (result,) = run(fake, ["https://a.org/x"], rate=100, retries=2)
    assert result["status"] == 503 and result["attempts"] == 3
    waits = [s for s in fake.sleeps if s >= 0.5]
    assert len(waits) == 2 and waits[1] > waits[0]


def test_client_errors_are_not_retried_but_network_errors_are():
    fake = Fake({"https://a.org/missing": [(404, {}, b"", "HTTP 404")],
                 "https://a.org/down": [(0, {}, b"", "refused"), (200, {}, b"up", "")]})
    results = run(fake, ["https://a.org/missing", "https://a.org/down"], rate=100)
    assert [r["attempts"] for r in results] == [1, 2] and results[1]["status"] == 200


class Handler(BaseHTTPRequestHandler):
    hits = 0

    def log_message(self, *args):
        pass

    def do_GET(self):
        Handler.hits += 1
        if self.path == "/limited" and Handler.hits == 1:
            self.send_response(429)
            self.send_header("Retry-After", "0")
            self.end_headers()
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"hello")


def test_real_server_cli_saves_files(tmp_path, capsys):
    Handler.hits = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        out = tmp_path / "pages"
        assert rlf.main([f"{base}/limited", f"{base}/page.html", "--rate", "50", "--apply",
                         "--backoff", "0", "-o", str(out)]) == 0
        text = capsys.readouterr().out
        assert "retry 1/3" in text and "2 fetched, 0 failed." in text
        assert (out / "page.html").read_bytes() == b"hello"
    finally:
        server.shutdown()


def test_plan_makes_no_requests(capsys):
    assert rlf.main(["https://a.org/1", "https://a.org/2", "https://b.org/1", "bad", "--rate",
                     "2"]) == 0
    out = capsys.readouterr().out
    assert "3 URL(s) on 2 site(s), 2 request(s)/second per site" in out
    assert "t+  0.5s  https://a.org/2" in out and "t+  0.0s  https://b.org/1" in out
    assert "Plan only: about 0.5s" in out
    assert rlf.main(["bad"]) == 1
    with pytest.raises(SystemExit):
        rlf.main(["https://a.org", "--rate", "0"])
