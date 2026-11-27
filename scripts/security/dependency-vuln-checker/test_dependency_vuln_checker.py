import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import dependency_vuln_checker as dvc
import pytest

REQUIREMENTS = """# pinned
requests==2.19.0
Flask[async]==2.0.1 ; python_version >= "3.8"
jinja2>=3.0
numpy==1.26.4  # inline comment
-r other.txt
--index-url https://example.com/simple
git+https://github.com/x/y.git
left_pad===1.0.0
unpinned
"""
DB = {
    "PyPI:requests": [{"id": "DEMO-1", "summary": "header leak", "severity": "HIGH",
                       "introduced": "0", "fixed": "2.20.0"}],
    "PyPI:flask": [{"id": "DEMO-2", "summary": "debug page", "severity": "MEDIUM",
                    "introduced": "2.0.0", "fixed": "2.0.3", "aliases": ["CVE-0000-0001"]}],
    "PyPI:left-pad": [{"id": "DEMO-3", "summary": "never fixed", "severity": "LOW",
                       "introduced": "1.0.0"}],
    "npm:lodash": [{"id": "DEMO-4", "summary": "prototype pollution", "severity": "CRITICAL",
                    "introduced": "0", "fixed": "4.17.21"}]}


def test_normalise_names():
    assert dvc.normalise("Flask_Login.Ext", "PyPI") == "flask-login-ext"
    assert dvc.normalise("Left_Pad", "npm") == "Left_Pad"


def test_parse_requirements_keeps_pins_and_reports_the_rest():
    deps, skipped = dvc.parse_requirements(REQUIREMENTS)
    assert [(d["name"], d["version"], d["line"]) for d in deps] == [
        ("requests", "2.19.0", 2), ("Flask", "2.0.1", 3), ("numpy", "1.26.4", 5),
        ("left_pad", "1.0.0", 9)]
    assert skipped == ["jinja2>=3.0 (not pinned with ==)", "unpinned (not pinned with ==)"]


def test_parse_package_json_exact_versions_only():
    text = json.dumps({"dependencies": {"lodash": "4.17.20", "express": "^4.18.0"},
                       "devDependencies": {"jest": "29.7.0-beta.1", "eslint": "~8.0.0"}})
    deps, skipped = dvc.parse_package_json(text)
    assert [(d["name"], d["version"]) for d in deps] == [("lodash", "4.17.20"),
                                                         ("jest", "29.7.0-beta.1")]
    assert len(skipped) == 2 and "express@^4.18.0" in skipped[0]
    assert all(d["ecosystem"] == "npm" for d in deps)


def test_parse_package_lock_uses_resolved_versions():
    text = json.dumps({"packages": {
        "": {"name": "app", "version": "1.0.0"},
        "node_modules/lodash": {"version": "4.17.20"},
        "node_modules/a/node_modules/lodash": {"version": "4.17.20"},
        "node_modules/@scope/pkg": {"version": "1.2.3"},
        "node_modules/aliased": {"name": "real-name", "version": "2.0.0"}}})
    deps, skipped = dvc.parse_package_lock(text)
    assert [(d["name"], d["version"]) for d in deps] == [
        ("lodash", "4.17.20"), ("@scope/pkg", "1.2.3"), ("real-name", "2.0.0")]  # no duplicates
    assert skipped == []


@pytest.mark.parametrize("version,expected", [
    ("1.2.3", (1, 2, 3)), ("1.10.0rc1", (1, 10, 0)), ("2.0.0+local.1", (2, 0, 0)),
    ("v3.1", (3, 1)), ("v", (0,)), ("1.0.0.post2", (1, 0, 0)), ("2024.1", (2024, 1))])
def test_version_key(version, expected):
    assert dvc.version_key(version) == expected
    assert dvc.version_key("1.10.0") > dvc.version_key("1.9.9")  # numbers, not text


def test_from_db_matches_only_affected_versions():
    def dep(name, version, eco="PyPI"):
        return {"name": name, "version": version, "ecosystem": eco}

    assert [a["id"] for a in dvc.from_db(DB, dep("requests", "2.19.0"))] == ["DEMO-1"]
    assert dvc.from_db(DB, dep("requests", "2.20.0")) == []  # fixed version is safe
    assert dvc.from_db(DB, dep("Requests", "1.0")) != []  # name matching ignores case
    assert dvc.from_db(DB, dep("flask", "1.9.9")) == []  # before it was introduced
    assert dvc.from_db(DB, dep("flask", "2.0.2"))[0]["aliases"] == ["CVE-0000-0001"]
    assert dvc.from_db(DB, dep("left_pad", "9.9.9"))[0]["fixed"] == []  # never fixed
    assert dvc.from_db(DB, dep("lodash", "4.17.20", "npm"))[0]["severity"] == "critical"
    assert dvc.from_db(DB, dep("unknown-pkg", "1.0")) == []


def test_summarise_vuln_picks_the_fix_for_this_package():
    vuln = {"id": "GHSA-1", "aliases": ["CVE-1"], "details": "A  long\n description " * 20,
            "database_specific": {"severity": "HIGH"},
            "affected": [
                {"package": {"name": "other", "ecosystem": "PyPI"},
                 "ranges": [{"events": [{"introduced": "0"}, {"fixed": "9.9"}]}]},
                {"package": {"name": "My_Pkg", "ecosystem": "PyPI"},
                 "ranges": [{"events": [{"introduced": "0"}, {"fixed": "1.10.0"}]},
                            {"events": [{"fixed": "1.2.0"}]}]}]}
    summary = dvc.summarise_vuln(vuln, {"name": "my-pkg", "ecosystem": "PyPI"})
    assert summary["fixed"] == ["1.2.0", "1.10.0"] and summary["severity"] == "high"
    assert len(summary["summary"]) <= 100 and "\n" not in summary["summary"]
    bare = dvc.summarise_vuln({"id": "X", "summary": "short"}, {"name": "p", "ecosystem": "npm"})
    assert bare["severity"] == "unknown" and bare["summary"] == "short"


class FakeOSV(BaseHTTPRequestHandler):
    requests = []

    def log_message(self, *args):
        pass

    def reply(self, body):
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeOSV.requests.append(body)
        results = []
        for query in body["queries"]:
            vulnerable = query["package"]["name"] == "requests" and query["version"] == "2.19.0"
            results.append({"vulns": [{"id": "GHSA-demo", "modified": "2026-01-01"}]}
                           if vulnerable else {})
        self.reply({"results": results})

    def do_GET(self):
        self.reply({"id": "GHSA-demo", "aliases": ["CVE-2026-0001"], "summary": "Demo issue",
                    "database_specific": {"severity": "HIGH"},
                    "affected": [{"package": {"name": "requests", "ecosystem": "PyPI"},
                                  "ranges": [{"events": [{"introduced": "0"},
                                                         {"fixed": "2.20.0"}]}]}]})


@pytest.fixture
def osv_url():
    FakeOSV.requests.clear()
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOSV)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_live_lookup_against_a_fake_osv(tmp_path, osv_url, capsys):
    path = tmp_path / "requirements.txt"
    path.write_text(REQUIREMENTS, encoding="utf-8")
    assert dvc.main([str(path), "--osv-url", osv_url]) == 1
    out = capsys.readouterr().out
    assert "Checked 4 pinned package(s)" in out
    assert "[HIGH] requests==2.19.0: GHSA-demo (CVE-2026-0001)" in out and "fixed in 2.20.0" in out
    assert "Not checked (2)" in out
    sent = FakeOSV.requests[0]["queries"]
    assert {"package": {"name": "requests", "ecosystem": "PyPI"}, "version": "2.19.0"} in sent
    assert all(set(q) == {"package", "version"} for q in sent)  # nothing else leaves the machine


def test_a_clean_run_exits_zero(tmp_path, osv_url, capsys):
    path = tmp_path / "requirements.txt"
    path.write_text("requests==2.31.0\nnumpy==1.26.4\n", encoding="utf-8")
    assert dvc.main([str(path), "--osv-url", osv_url]) == 0
    assert "No known vulnerabilities" in capsys.readouterr().out


def test_cli_with_a_saved_database(tmp_path, capsys):
    path = tmp_path / "requirements.txt"
    path.write_text("requests==2.19.0\nflask==2.0.1\nleft-pad==1.0.0\nnumpy==1.26.4\n")
    db = tmp_path / "db.json"
    db.write_text(json.dumps(DB))
    assert dvc.main([str(path), "--db", str(db)]) == 1
    out = capsys.readouterr().out
    assert out.index("[HIGH] requests") < out.index("[MEDIUM] flask") < out.index("[LOW] left-pad")
    assert "no fixed version listed" in out and "saved database db.json" in out
    assert dvc.main([str(path), "--db", str(db), "--fail-on", "critical"]) == 0
    capsys.readouterr()
    assert dvc.main([str(path), "--db", str(db), "--ignore", "DEMO-1", "--ignore",
                     "CVE-0000-0001", "--ignore", "DEMO-3"]) == 0
    assert "No known vulnerabilities" in capsys.readouterr().out
    assert dvc.main([str(path), "--db", str(db), "--format", "json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["checked"] == 4 and [f["id"] for f in data["findings"]] == [
        "DEMO-1", "DEMO-2", "DEMO-3"]


def test_package_lock_through_the_cli(tmp_path, capsys):
    lock = tmp_path / "package-lock.json"
    packages = {"": {}, "node_modules/lodash": {"version": "4.17.20"}}
    lock.write_text(json.dumps({"packages": packages}))
    db = tmp_path / "db.json"
    db.write_text(json.dumps(DB))
    assert dvc.main([str(lock), "--db", str(db)]) == 1
    assert "[CRITICAL] lodash==4.17.20: DEMO-4" in capsys.readouterr().out


def test_errors(tmp_path, capsys):
    empty = tmp_path / "requirements.txt"
    empty.write_text("# nothing pinned\nrequests>=2\n")
    assert dvc.main([str(empty), "--db", str(tmp_path / "db.json")]) == 1
    assert "No exactly pinned" in capsys.readouterr().err
    pinned = tmp_path / "pinned.txt"
    pinned.write_text("requests==2.19.0\n")
    assert dvc.main([str(pinned), "--db", str(tmp_path / "missing.json")]) == 1
    assert "Can't check" in capsys.readouterr().err
    assert dvc.main([str(tmp_path / "none.txt")]) == 1
    assert dvc.main([str(pinned), "--osv-url", "ftp://example.com"]) == 1
    assert "http://" in capsys.readouterr().err
    assert dvc.main([str(pinned), "--osv-url", "http://127.0.0.1:9"]) == 1  # nothing listens there
    assert "Can't check" in capsys.readouterr().err
