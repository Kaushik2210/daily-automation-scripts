import csv
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import star_tracker as st


def repo(name, stars, forks=0, fork=False):
    return {"full_name": f"me/{name}", "stargazers_count": stars, "forks_count": forks,
            "fork": fork}


REPOS = [repo("a", 120, 3), repo("b", 50), repo("c", 7, fork=True), {"stargazers_count": 1}]


def test_snapshot_skips_forks_and_nameless_entries():
    assert st.snapshot(REPOS) == {"me/a": (120, 3), "me/b": (50, 0)}
    assert "me/c" in st.snapshot(REPOS, include_forks=True)


def test_read_log_groups_sorts_and_ignores_bad_rows(tmp_path):
    log = tmp_path / "stars.csv"
    log.write_text("date,repo,stars,forks\n2026-02-01,me/a,10,1\n2026-01-01,me/a,5,0\n"
                   "bad,me/a,notnumber,0\n2026-01-01,me/b,3,\n")
    assert st.read_log(log) == {"me/a": [("2026-01-01", 5, 0), ("2026-02-01", 10, 1)],
                                "me/b": [("2026-01-01", 3, 0)]}
    assert st.read_log(tmp_path / "missing.csv") == {} and st.read_log(None) == {}


def test_compare_uses_the_latest_earlier_reading():
    history = {"me/a": [("2026-01-01", 100, 0), ("2026-02-01", 110, 0), ("2026-03-05", 999, 0)]}
    rows = st.compare({"me/a": (120, 0), "me/new": (5, 0)}, history, "2026-03-01")
    assert rows == [("me/a", 120, 10, "2026-02-01"), ("me/new", 5, None, None)]


def test_record_adds_once_per_day(tmp_path):
    log = tmp_path / "stars.csv"
    current = {"me/a": (120, 3), "me/b": (50, 0)}
    assert st.record(log, current, {}, "2026-03-01") == 2
    assert st.record(log, current, st.read_log(log), "2026-03-01") == 0
    assert st.record(log, {"me/a": (125, 3)}, st.read_log(log), "2026-03-02") == 1
    rows = list(csv.reader(log.open()))
    assert rows[0] == st.HEADER and len(rows) == 4
    assert rows[-1] == ["2026-03-02", "me/a", "125", "3"]


def test_cli_first_run_then_growth(tmp_path, capsys):
    src, log = tmp_path / "repos.json", tmp_path / "log.csv"
    src.write_text(json.dumps(REPOS))
    base = ["--from-file", str(src), "--log", str(log)]
    assert st.main([*base, "--today", "2026-03-01"]) == 0
    out = capsys.readouterr().out
    assert "first reading" in out and "Saved 2 row(s)" in out
    src.write_text(json.dumps([repo("a", 130, 3), repo("b", 49)]))
    assert st.main([*base, "--today", "2026-03-08"]) == 0
    out = capsys.readouterr().out
    assert "+10 since 2026-03-01" in out and "-1 since 2026-03-01" in out
    assert "Total" in out and "+9 across repos with history" in out


def test_no_record_leaves_the_log_alone(tmp_path):
    src, log = tmp_path / "repos.json", tmp_path / "log.csv"
    src.write_text(json.dumps(REPOS))
    assert st.main(["--from-file", str(src), "--log", str(log), "--no-record"]) == 0
    assert not log.exists()


def test_bad_input(tmp_path, capsys):
    src = tmp_path / "r.json"
    src.write_text('{"message": "Not Found"}')
    assert st.main(["--from-file", str(src)]) == 1
    src.write_text("[]")
    assert st.main(["--from-file", str(src)]) == 1
    with pytest.raises(SystemExit):
        st.main([])


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        host = f"http://127.0.0.1:{self.server.server_address[1]}"
        if self.path.startswith("/users/me/repos") and "page=2" not in self.path:
            body, link = REPOS[:1], f'<{host}/users/me/repos?page=2>; rel="next"'
        elif "page=2" in self.path:
            body, link = REPOS[1:2], ""
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        if link:
            self.send_header("Link", link)
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())


def test_live_user_with_paging_and_404(monkeypatch, capsys):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    monkeypatch.setattr(st, "API", f"http://127.0.0.1:{httpd.server_address[1]}")
    try:
        assert st.main(["me", "--today", "2026-03-01"]) == 0
        out = capsys.readouterr().out
        assert "me/a" in out and "me/b" in out
        assert st.main(["nobody"]) == 1
        assert "user not found" in capsys.readouterr().err
    finally:
        httpd.shutdown()
