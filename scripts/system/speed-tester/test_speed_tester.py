import contextlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import speed_tester as st


class Files(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.startswith("/missing"):
            self.send_error(404)
            return
        size = 300_000
        self.send_response(200)
        self.send_header("Content-Length", str(size))
        self.end_headers()
        with contextlib.suppress(OSError):  # the client may stop reading early
            self.wfile.write(b"x" * size)


@pytest.fixture
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Files)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def test_mbps_and_formatting():
    assert st.mbps(25_000_000, 2.0) == 100.0 and st.mbps(10, 0) == 0.0
    assert st.megabytes(2_500_000) == 2.5


def test_download_counts_every_byte(server):
    result = st.download(server + "/file", 0, 30, 5)
    assert result["bytes"] == 300_000 and result["seconds"] > 0
    assert 0 < result["first_byte"] <= result["seconds"] and result["mbps"] > 0


def test_download_respects_limits(server):
    limited = st.download(server + "/file", 100_000, 30, 5)
    assert 100_000 <= limited["bytes"] < 300_000
    ticks = iter(range(0, 1000, 5))  # a fake clock that jumps 5 s per reading
    timed = st.download(server + "/file", 0, 7, 5, clock=lambda: float(next(ticks)))
    assert 0 < timed["bytes"] < 300_000  # the time limit stopped it after the first chunk


def test_parse_saved():
    runs = st.parse_saved("# header\n25000000 2.5\n\n10000, 1  # comment is dropped\n")
    assert [r["bytes"] for r in runs] == [25000000, 10000]
    assert runs[0]["mbps"] == 80.0
    for bad in ("one two", "5", "0 1", "100 -2"):
        with pytest.raises(ValueError):
            st.parse_saved(bad)


def test_summarise():
    runs = st.parse_saved("1000000 1\n1000000 2\n1000000 4")
    s = st.summarise(runs)
    assert (s["runs"], s["best"], s["worst"], s["median"]) == (3, 8.0, 2.0, 4.0)
    assert s["average"] == pytest.approx(14 / 3)


def test_cli_live_run_with_log_and_minimum(server, tmp_path, capsys):
    log = tmp_path / "speed.csv"
    argv = ["--url", server + "/file", "--runs", "2", "--log", str(log)]
    assert st.main(argv) == 0
    out = capsys.readouterr().out
    assert "2 run(s): average" in out and "Appended 2 row(s)" in out and "300000" not in out
    assert st.main([*argv, "--min-mbps", "999999"]) == 1
    assert "below the 999999 Mbit/s minimum" in capsys.readouterr().err
    lines = log.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "time,url,bytes,seconds,mbps" and len(lines) == 1 + 2 + 2


def test_cli_saved_timings_and_errors(server, tmp_path, capsys):
    saved = tmp_path / "runs.txt"
    saved.write_text("25000000 2.0\n25000000 4.0\n")
    assert st.main(["--from-file", str(saved)]) == 0
    out = capsys.readouterr().out
    assert "100.0 Mbit/s" in out and "average 75.0 Mbit/s" in out
    assert st.main(["--url", server + "/missing"]) == 1
    assert "Speed test failed" in capsys.readouterr().err
    assert st.main(["--from-file", str(tmp_path / "none.txt")]) == 1
    empty = tmp_path / "empty.txt"
    empty.write_text("# nothing\n")
    assert st.main(["--from-file", str(empty)]) == 1
    for argv in (["--url", "file:///etc/passwd"], ["--url", "ftp://x/y"], ["--runs", "0"]):
        with pytest.raises(SystemExit):
            st.main(argv)
