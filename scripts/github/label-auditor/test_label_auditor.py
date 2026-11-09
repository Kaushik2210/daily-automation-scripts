import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import label_auditor as la
import pytest


def label(name, color="ffffff", description=""):
    return {"name": name, "color": color, "description": description}


SAME = {"o/a": [label("bug", "d73a4a", "Broken"), label("docs")],
        "o/b": [label("bug", "D73A4A", "Broken"), label("docs")]}
DIFFERENT = {
    "o/a": [label("bug", "d73a4a", "Broken"), label("docs"), label("only-a", "111111")],
    "o/b": [label("Bug", "ee0701", "Something broke"), label("docs", "ffffff", "Docs"),
            label("ux")],
    "o/c": [label("bug", "d73a4a", "Broken"), label("docs")]}


def test_normalise_ignores_case_and_punctuation():
    assert la.normalise("Good First-Issue") == la.normalise("good first issue") == "goodfirstissue"


def test_identical_labels_have_no_findings():
    findings, total = la.audit(SAME)
    assert total == 2 and not any(findings.values())


def test_findings_cover_missing_case_colour_and_description():
    findings, total = la.audit(DIFFERENT)
    assert total == 4
    missing = {name: absent for name, absent, _ in findings["missing"]}
    assert missing == {"only-a": ["o/b", "o/c"], "ux": ["o/a", "o/c"]}
    assert findings["case"] == [("Bug", {"o/a": "bug", "o/b": "Bug", "o/c": "bug"})]
    assert findings["color"][0][0] == "Bug"
    assert findings["color"][0][1] == {"o/a": "d73a4a", "o/b": "ee0701", "o/c": "d73a4a"}
    assert {name for name, _ in findings["description"]} == {"Bug", "docs"}


def test_report_text_and_problem_count():
    findings, total = la.audit(DIFFERENT)
    text, problems = la.report(findings, total, list(DIFFERENT))
    assert text.startswith("Compared 3 repositories and 4 distinct label(s).")
    assert "'only-a': missing in o/b, o/c" in text and "a=(none)" in text
    assert "Bug" in text and f"{problems} difference(s) found." in text
    clean, zero = la.report(*la.audit(SAME), ["o/a", "o/b"])
    assert zero == 0 and clean.endswith("All labels match.")


def test_cli_from_file(tmp_path, capsys):
    f = tmp_path / "labels.json"
    f.write_text(json.dumps(DIFFERENT))
    assert la.main(["--from-file", str(f)]) == 1
    assert "Missing from some repositories (2):" in capsys.readouterr().out
    f.write_text(json.dumps(SAME))
    assert la.main(["--from-file", str(f)]) == 0
    f.write_text(json.dumps({"o/a": []}))
    assert la.main(["--from-file", str(f)]) == 1
    f.write_text("[]")
    assert la.main(["--from-file", str(f)]) == 1
    with pytest.raises(SystemExit):
        la.main([])
    with pytest.raises(SystemExit):
        la.main(["bad repo", "o/b"])


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        repo = "/".join(self.path.split("?")[0].split("/")[2:4])
        host = f"http://127.0.0.1:{self.server.server_address[1]}"
        if repo not in DIFFERENT:
            self.send_response(404)
            self.end_headers()
            return
        labels = DIFFERENT[repo]
        link = ""
        if "page=2" in self.path:
            labels = labels[1:]
        elif len(labels) > 1:
            labels, link = labels[:1], f'<{host}{self.path.split("?")[0]}?page=2>; rel="next"'
        self.send_response(200)
        if link:
            self.send_header("Link", link)
        self.end_headers()
        self.wfile.write(json.dumps(labels).encode())


def test_live_fetch_follows_paging_and_reports_404(monkeypatch, capsys):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    monkeypatch.setattr(la, "API", f"http://127.0.0.1:{httpd.server_address[1]}")
    try:
        assert [x["name"] for x in la.fetch_labels("o/a")] == ["bug", "docs", "only-a"]
        assert la.main(["o/a", "o/b", "o/c"]) == 1
        assert "difference(s) found" in capsys.readouterr().out
        assert la.main(["o/a", "o/missing"]) == 1
        assert "404 (not found)" in capsys.readouterr().err
    finally:
        httpd.shutdown()
