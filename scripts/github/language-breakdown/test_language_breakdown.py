import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import language_breakdown as lb
import pytest


def repo(name, language, stars=0, size=0, **extra):
    return {"name": name, "full_name": f"me/{name}", "language": language,
            "stargazers_count": stars, "size": size, **extra}


REPOS = [repo("a", "Python", 10, 500), repo("b", "Python", 5, 100), repo("c", "Go", 100, 50),
         repo("d", None, 1, 5), repo("e", "Rust", 7, 40, fork=True),
         repo("f", "Perl", 0, 0, archived=True)]


def test_tally_by_count_stars_and_size():
    assert lb.tally(REPOS) == {"Python": 2, "Go": 1, "Perl": 1}
    assert lb.tally(REPOS, "stars") == {"Python": 15, "Go": 100}  # zero-weight entries drop out
    assert lb.tally(REPOS, "size") == {"Python": 600, "Go": 50}


def test_tally_filters():
    assert "Rust" in lb.tally(REPOS, include_forks=True)
    assert "Perl" not in lb.tally(REPOS, include_archived=False)


def test_render_shares_and_bars():
    text = lb.render(lb.Counter({"Python": 3, "Go": 1}), "repo(s)", width=20)
    first, second = text.splitlines()
    assert first.startswith("Python") and "75.0%" in first and first.count("#") == 15
    assert "25.0%" in second and second.count("#") == 5 and second.endswith("1 repo(s)")
    assert lb.render(lb.Counter({"X": 1, "Y": 10_000}), "u", 10).count("#") == 11  # min one bar


def test_cli_from_file(tmp_path, capsys):
    f = tmp_path / "repos.json"
    f.write_text(json.dumps(REPOS))
    assert lb.main(["--from-file", str(f)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("Languages by count:") and "Python" in out and "50.0%" in out
    assert lb.main(["--from-file", str(f), "--weight", "size", "--skip-archived"]) == 0
    assert "KB" in capsys.readouterr().out
    f.write_text("[]")
    assert lb.main(["--from-file", str(f)]) == 1


def test_argument_errors(tmp_path):
    f = tmp_path / "r.json"
    f.write_text("[]")
    with pytest.raises(SystemExit):
        lb.main([])
    with pytest.raises(SystemExit):
        lb.main(["--from-file", str(f), "--bytes"])


class Handler(BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        Handler.seen.append(self.path)
        bodies = {"/users/me/repos": REPOS[:3],
                  "/repos/me/a/languages": {"Python": 9000, "Shell": 1000},
                  "/repos/me/b/languages": {"Python": 1000},
                  "/repos/me/c/languages": {"Go": 5000}}
        body = bodies.get(self.path.split("?")[0])
        self.send_response(200 if body is not None else 404)
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())


@pytest.fixture
def server(monkeypatch):
    Handler.seen = []
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    monkeypatch.setattr(lb, "API", f"http://127.0.0.1:{httpd.server_address[1]}")
    yield httpd
    httpd.shutdown()


def test_live_bytes_mode_sums_per_language(server, capsys):
    assert lb.main(["me", "--bytes"]) == 0
    out = capsys.readouterr().out
    assert "Languages by code bytes" in out and "Python" in out and "10,000 bytes" in out
    assert any(p.endswith("/repos/me/c/languages") for p in Handler.seen)


def test_live_max_repos_and_missing_user(server, capsys):
    assert lb.main(["me", "--bytes", "--max-repos", "1"]) == 0
    assert not any("/repos/me/c/" in p for p in Handler.seen)
    assert lb.main(["ghost"]) == 1
    assert "404" in capsys.readouterr().err
