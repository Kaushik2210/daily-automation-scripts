import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import release_notifier as rn


def release(tag, pre=False, draft=False, body=""):
    return {"tag_name": tag, "name": f"Release {tag}", "prerelease": pre, "draft": draft,
            "body": body, "published_at": "2026-11-03T10:00:00Z",
            "html_url": f"https://github.com/o/r/releases/tag/{tag}"}


def test_classify_every_outcome():
    state = {"o/a": "v1", "o/b": "v1"}
    assert rn.classify("o/a", None, state) == ("none", "")
    assert rn.classify("o/a", release("v1"), state) == ("unchanged", "v1")
    assert rn.classify("o/a", release("v2"), state) == ("new", "v2")
    assert rn.classify("o/c", release("v1"), state) == ("baseline", "v1")
    assert rn.classify("o/a", release("v2-rc", pre=True), state) == ("skipped", "v2-rc")
    assert rn.classify("o/a", release("v2-rc", pre=True), state, True) == ("new", "v2-rc")


def test_first_lines_strips_markdown_markers():
    assert rn.first_lines("## Changes\n\n- one\n* two\nthree\nfour", 3) == ["Changes", "one", "two"]
    assert rn.first_lines(None) == []


def test_read_names_ignores_comments(tmp_path):
    f = tmp_path / "repos.txt"
    f.write_text("# watched\no/a\n\n o/b \n")
    assert rn.read_names(f) == ["o/a", "o/b"]


def write(path, data):
    path.write_text(json.dumps(data))
    return str(path)


def test_saved_mode_reports_new_and_updates_state(tmp_path, capsys):
    saved = write(tmp_path / "rel.json", {"o/a": release("v2", body="- faster\n- fixes"),
                                          "o/b": release("v1"), "o/c": None,
                                          "o/d": release("v0.1-rc", pre=True)})
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"o/a": "v1", "o/b": "v1"}))
    assert rn.main(["--releases", saved, "--state", str(state)]) == 1  # a new release exists
    out = capsys.readouterr().out
    assert "*  o/a: NEW v2" in out and "faster" in out and "releases/tag/v2" in out
    assert "o/b: v1 (nothing new)" in out and "o/c: no releases yet" in out
    assert "o/d: v0.1-rc is a pre-release, ignored" in out
    assert "1 new release(s) across 4 repositories." in out
    assert json.loads(state.read_text()) == {"o/a": "v2", "o/b": "v1"}
    assert rn.main(["--releases", saved, "--state", str(state)]) == 0  # nothing new now


def test_first_run_is_a_baseline_unless_report_all(tmp_path, capsys):
    saved = write(tmp_path / "rel.json", {"o/a": release("v1")})
    state = tmp_path / "state.json"
    assert rn.main(["--releases", saved, "--state", str(state)]) == 0
    assert "(first look, remembered)" in capsys.readouterr().out
    assert json.loads(state.read_text()) == {"o/a": "v1"}
    assert rn.main(["--releases", saved, "--report-all"]) == 1
    assert "NEW v1" in capsys.readouterr().out


def test_no_update_keeps_the_state(tmp_path):
    saved = write(tmp_path / "rel.json", {"o/a": release("v2")})
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"o/a": "v1"}))
    assert rn.main(["--releases", saved, "--state", str(state), "--no-update"]) == 1
    assert json.loads(state.read_text()) == {"o/a": "v1"}


def test_bad_input(tmp_path, capsys):
    with pytest.raises(SystemExit):
        rn.main([])
    with pytest.raises(SystemExit):
        rn.main(["not a repo"])
    broken = tmp_path / "x.json"
    broken.write_text("[1, 2]")
    assert rn.main(["--releases", str(broken)]) == 1
    assert "Couldn't read the input" in capsys.readouterr().err


class Handler(BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        Handler.seen.append(self.path)
        bodies = {"/repos/o/a/releases/latest": release("v3"),
                  "/repos/o/a/releases": [release("v4-draft", draft=True),
                                          release("v3-rc", pre=True)],
                  "/repos/o/none/releases/latest": None}
        if self.path.split("?")[0] == "/repos/o/boom/releases/latest":
            self.send_response(500)
            self.end_headers()
            return
        body = bodies.get(self.path.split("?")[0])
        self.send_response(200 if body is not None else 404)
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())


@pytest.fixture
def server(monkeypatch):
    Handler.seen = []
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    monkeypatch.setattr(rn, "API", f"http://127.0.0.1:{httpd.server_address[1]}")
    yield httpd
    httpd.shutdown()


def test_live_lookup_variants(server):
    assert rn.latest_release("o/a")["tag_name"] == "v3"
    assert rn.latest_release("o/a", include_prereleases=True)["tag_name"] == "v3-rc"  # skips drafts
    assert rn.latest_release("o/none") is None


def test_live_cli_reports_errors_per_repo(server, tmp_path, capsys):
    state = tmp_path / "s.json"
    state.write_text(json.dumps({"o/a": "v2"}))
    assert rn.main(["o/a", "o/boom", "--state", str(state)]) == 1
    out = capsys.readouterr().out
    assert "NEW v3" in out and "o/boom: couldn't check" in out
    assert json.loads(state.read_text()) == {"o/a": "v3"}
