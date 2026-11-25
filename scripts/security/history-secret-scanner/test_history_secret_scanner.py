import json
import shutil
import subprocess

import history_secret_scanner as hss
import pytest

PATCH = """commit bbbb2222
Author: Dev Two <two@example.com>
Date:   Tue Nov 4 2026

    remove it

diff --git a/cfg.env b/cfg.env
--- a/cfg.env
+++ b/cfg.env
@@ -1,2 +1 @@
-DB_PASSWORD = "hunter2-hunter2"
 KEEP=1

commit aaaa1111
Author: Dev One <one@example.com>
Date:   Mon Nov 3 2026

    add config

diff --git a/cfg.env b/cfg.env
new file mode 100644
--- /dev/null
+++ b/cfg.env
@@ -0,0 +1,3 @@
+DB_PASSWORD = "hunter2-hunter2"
+KEY=AKIAIOSFODNN7EXAMPLE
+KEEP=1
diff --git a/keys/id b/keys/id
new file mode 100644
--- /dev/null
+++ b/keys/id
@@ -0,0 +1 @@
+-----BEGIN OPENSSH PRIVATE KEY-----
"""


def test_mask_never_shows_everything():
    assert hss.mask("short") == "short"
    masked = hss.mask("AKIAABCDEFGHIJKLMNOP")
    assert masked.startswith("AKI") and masked.endswith("NOP") and "DEFGH" not in masked


def test_find_secrets_and_placeholders():
    assert hss.find_secrets('password = "correct-horse-battery"') == [
        ("Hard-coded credential", "correct-horse-battery")]
    assert hss.find_secrets('password = "your_password_here"') == []
    assert hss.find_secrets("k=AKIAIOSFODNN7EXAMPLE") == []
    assert hss.find_secrets("k=AKIAIOSFODNN7EXAMPLE", True)[0][0] == "AWS access key"
    assert hss.find_secrets("nothing here") == []


def test_scan_patch_attributes_commit_and_removal():
    findings = hss.scan_patch(PATCH)
    by_kind = {f["kind"]: f for f in findings}
    assert set(by_kind) == {"Hard-coded credential", "Private key block"}
    password = by_kind["Hard-coded credential"]
    assert password["commit"] == "aaaa1111" and password["path"] == "cfg.env"
    assert password["author"] == "Dev One <one@example.com>"
    assert password["removed_in"] == "bbbb2222" and "hunter2-hunter2" not in json.dumps(findings)
    key = by_kind["Private key block"]
    assert key["path"] == "keys/id" and key["removed_in"] is None
    assert len(hss.scan_patch(PATCH, include_placeholders=True)) == 3


def test_removed_lines_alone_are_not_findings():
    assert hss.scan_patch(PATCH.split("commit aaaa1111")[0]) == []


def test_cli(tmp_path, capsys):
    saved = tmp_path / "p.patch"
    saved.write_text(PATCH)
    assert hss.main(["--from-file", str(saved)]) == 1
    out = capsys.readouterr().out
    assert "2 possible secret(s)" in out and "removed in bbbb2222" in out
    assert "still present in a later version" in out and "rotate it first" in out
    assert hss.main(["--from-file", str(saved), "--exit-zero", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["count"] == 2
    clean = tmp_path / "c.patch"
    clean.write_text("commit cccc3333\nAuthor: A\nDate: d\n\n    x\n")
    assert hss.main(["--from-file", str(clean)]) == 0
    assert "No secrets found" in capsys.readouterr().out
    assert hss.main(["--from-file", str(tmp_path / "none")]) == 1


@pytest.mark.skipif(not shutil.which("git"), reason="git is not installed")
def test_real_repository_finds_deleted_secret(tmp_path, capsys, monkeypatch):
    for key, value in (("NAME", "T"), ("EMAIL", "t@example.com")):
        monkeypatch.setenv(f"GIT_AUTHOR_{key}", value)
        monkeypatch.setenv(f"GIT_COMMITTER_{key}", value)

    def run(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

    run("init", "-q", "-b", "main")
    (tmp_path / "app.cfg").write_text('token = "s3cr3t-value-0001"\nname=x\n')
    run("add", ".")
    run("commit", "-q", "-m", "add")
    (tmp_path / "app.cfg").write_text("name=x\n")
    run("commit", "-q", "-am", "clean up")
    assert hss.main(["--repo", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "app.cfg" in out and "still in history" in out and "s3cr3t-value-0001" not in out
    assert hss.main(["--repo", str(tmp_path), "--max-count", "1"]) == 0
    assert hss.main(["--repo", str(tmp_path / "missing")]) == 1
