import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import latency_benchmark as lb
import pytest


@pytest.mark.parametrize("p,expected", [(0, 10), (50, 30), (100, 50), (25, 20), (90, 46),
                                        (99, 49.6)])
def test_percentile_interpolates(p, expected):
    assert lb.percentile([10, 20, 30, 40, 50], p) == pytest.approx(expected)


def test_percentile_edge_cases():
    assert lb.percentile([7], 99) == 7
    with pytest.raises(ValueError):
        lb.percentile([], 50)


def test_summarise():
    stats = lb.summarise([30, 10, 20, 40, 50])
    assert (stats["count"], stats["min"], stats["max"], stats["median"]) == (5, 10, 50, 30)
    assert stats["mean"] == 30 and round(stats["stdev"], 2) == 15.81
    assert lb.summarise([5])["stdev"] == 0.0


def test_histogram():
    assert lb.histogram([5, 5, 5]) == [(5, 5, 3)]
    bins = lb.histogram([0, 1, 2, 3, 4, 5, 6, 7, 8, 80], bins=4)
    assert [c for _, _, c in bins] == [9, 0, 0, 1] and bins[-1][1] == 80


def test_benchmark_with_a_fake_call_counts_warmup_separately():
    calls = []

    def fake(url, method, timeout):
        calls.append(url)
        return 1.0, 200, ""

    results, wall = lb.benchmark("http://x", 7, 3, 2, "GET", 1, call=fake)
    assert len(results) == 7 and len(calls) == 9 and wall >= 0


def test_read_timings_text_and_csv(tmp_path):
    plain = tmp_path / "t.txt"
    plain.write_text("10\n20.5\n\n30\n")
    assert lb.read_timings(plain) == [10, 20.5, 30]
    table = tmp_path / "t.csv"
    table.write_text("ms,status,error\n12.5,200,\n15.0,200,\n,0,refused\n")
    assert lb.read_timings(table) == [12.5, 15.0]
    other = tmp_path / "o.csv"
    other.write_text("a,b\n1,2\n")
    with pytest.raises(ValueError, match="'ms' column"):
        lb.read_timings(other)


def test_summarise_cli(tmp_path, capsys):
    path = tmp_path / "t.txt"
    path.write_text("\n".join(str(v) for v in [80, 85, 90, 95, 100, 2000]))
    assert lb.main(["--summarise", str(path), "--slow", "500"]) == 0
    out = capsys.readouterr().out
    assert "6 sample(s), ms:  min 80.0" in out and "p99" in out and "Distribution (ms):" in out
    assert "1 sample(s) slower than 500 ms." in out
    empty = tmp_path / "e.txt"
    empty.write_text("")
    assert lb.main(["--summarise", str(empty)]) == 1
    bad = tmp_path / "b.txt"
    bad.write_text("fast")
    assert lb.main(["--summarise", str(bad)]) == 1
    with pytest.raises(SystemExit):
        lb.main(["--summarise", str(tmp_path / "none.txt")])


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/slow":
            time.sleep(0.05)
        self.send_response(500 if self.path == "/error" else 200)
        self.end_headers()
        self.wfile.write(b"ok")

    do_HEAD = do_GET


@pytest.fixture
def base():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_real_benchmark_measures_server_delay_and_saves_csv(base, tmp_path, capsys):
    target = tmp_path / "raw.csv"
    args = [f"{base}/slow", "-n", "10", "-c", "5", "--warmup", "1", "--csv", str(target)]
    assert lb.main(args) == 0
    out = capsys.readouterr().out
    assert "status codes: 200 x10" in out and "throughput:" in out and "p95" in out
    lines = target.read_text().splitlines()
    assert lines[0] == "ms,status,error" and len(lines) == 11
    assert min(float(line.split(",")[0]) for line in lines[1:]) >= 45  # the 50 ms server delay


def test_errors_set_the_exit_code(base, capsys):
    assert lb.main([f"{base}/error", "-n", "4", "--warmup", "0"]) == 1
    out = capsys.readouterr().out
    assert "status codes: 500 x4" in out and "No successful responses" in out
    assert lb.main(["http://127.0.0.1:9/", "-n", "2", "--warmup", "0", "--timeout", "1"]) == 1
    assert "no answer x2" in capsys.readouterr().out


def test_limits_and_arguments(tmp_path):
    with pytest.raises(SystemExit):
        lb.main([])
    with pytest.raises(SystemExit):
        lb.main(["ftp://x"])
    with pytest.raises(SystemExit):
        lb.main(["http://x", "-n", "999999"])
    with pytest.raises(SystemExit):
        lb.main(["http://x", "-c", "0"])
    existing = tmp_path / "e.csv"
    existing.write_text("x")
    with pytest.raises(SystemExit):
        lb.main(["http://x", "--csv", str(existing)])
