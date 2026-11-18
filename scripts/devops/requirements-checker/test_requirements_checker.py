import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import requirements_checker as rc

REQ = """# web
flask==2.0.1   # pinned
Requests[security]==2.31.0
numpy>=1.20
-r other.txt
Django_Rest.Framework==3.14.0
pytest == 8.0.0
"""


def test_parse_requirements():
    assert rc.parse_requirements(REQ) == [
        (2, "flask", "2.0.1"), (3, "Requests", "2.31.0"),
        (6, "Django_Rest.Framework", "3.14.0"), (7, "pytest", "8.0.0")]


def test_normalise_and_version_order():
    assert rc.normalise("Django_Rest.Framework") == "django-rest-framework"
    assert rc.version_key("1.10.0") > rc.version_key("1.9.9")
    assert rc.version_key("2.0") > rc.version_key("2.0rc1")
    assert rc.version_key("2.0.1") > rc.version_key("2.0")


@pytest.mark.parametrize("current,latest,kind", [
    ("2.0.1", "3.0.0", "major"), ("2.0.1", "2.1.0", "minor"), ("2.0.1", "2.0.5", "patch"),
    ("2.0", "2.0.1", "patch")])
def test_bump_kind(current, latest, kind):
    assert rc.bump(current, latest) == kind


def test_cli_with_saved_versions(tmp_path, capsys):
    req = tmp_path / "requirements.txt"
    req.write_text(REQ)
    latest = tmp_path / "latest.json"
    latest.write_text(json.dumps({"Flask": "3.0.3", "requests": "2.31.0",
                                  "django-rest-framework": "3.15.2"}))
    assert rc.main([str(req), "--latest", str(latest)]) == 1
    out = capsys.readouterr().out
    assert "!  flask" in out and "major update" in out and "ok Requests" in out
    assert "3.14.0     -> 3.15.2" in out and "minor update" in out
    assert "?  pytest" in out and "not in the version file" in out
    assert "4 pinned package(s): 2 outdated, 1 unchecked." in out
    latest.write_text(json.dumps({"flask": "2.0.1", "requests": "2.31.0",
                                  "django-rest-framework": "3.14.0", "pytest": "8.0.0"}))
    assert rc.main([str(req), "--latest", str(latest)]) == 0


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        versions = {"/flask/json": "3.0.3", "/pytest/json": "8.0.0"}
        if self.path in versions:
            body = json.dumps({"info": {"version": versions[self.path]}}).encode()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


def test_pypi_lookup_against_a_local_server(tmp_path, monkeypatch, capsys):
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("PYPI_URL", f"http://127.0.0.1:{server.server_address[1]}")
    try:
        req = tmp_path / "r.txt"
        req.write_text("flask==2.0.1\npytest==8.0.0\nghostpkg==1.0\n")
        assert rc.main([str(req)]) == 1
        out = capsys.readouterr().out
        assert "flask" in out and "major update" in out and "ok pytest" in out
        assert "?  ghostpkg" in out and "1 outdated, 1 unchecked" in out
    finally:
        server.shutdown()


def test_no_pins_and_bad_files(tmp_path, capsys):
    req = tmp_path / "r.txt"
    req.write_text("numpy>=1\n")
    assert rc.main([str(req)]) == 1
    assert "No pinned" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        rc.main([str(req), "--latest", str(tmp_path / "gone.json")])
