import json
import os

import integrity_monitor as im
import pytest


@pytest.fixture
def site(tmp_path):
    folder = tmp_path / "site"
    for rel, text in {"index.html": "<h1>hi</h1>", "app/main.py": "print(1)\n",
                      "logs/debug.log": "noise", "conf/settings.ini": "debug=0\n"}.items():
        (folder / rel).parent.mkdir(parents=True, exist_ok=True)
        (folder / rel).write_text(text)
    return folder


def test_scan_hashes_files_and_honours_excludes(site):
    files = im.scan(site, ["logs"])
    assert list(files) == ["app/main.py", "conf/settings.ini", "index.html"]
    assert files["index.html"]["size"] == 11 and len(files["index.html"]["sha256"]) == 64
    assert ("mode" in files["index.html"]) == (os.name == "posix")


def test_sign_changes_with_content_and_key():
    files = {"a": {"size": 1, "sha256": "x"}}
    assert im.sign(files, "k1") == im.sign(files, "k1") != im.sign(files, "k2")
    assert im.sign(files, "k1") != im.sign({"a": {"size": 1, "sha256": "y"}}, "k1")


def test_compare_modified_added_removed_and_permissions():
    old = {"same": {"sha256": "1", "mode": "0644"}, "edit": {"sha256": "1"},
           "gone": {"sha256": "1"}, "perm": {"sha256": "1", "mode": "0644"}}
    new = {"same": {"sha256": "1", "mode": "0644"}, "edit": {"sha256": "2"},
           "fresh": {"sha256": "3"}, "perm": {"sha256": "1", "mode": "0777"}}
    assert im.compare(old, new) == (["edit"], ["fresh"], ["gone"], ["perm"])


def run(site, baseline, *args):
    return im.main([args[0], str(site), "--baseline", str(baseline), *args[1:]])


def test_init_then_check_is_clean_and_init_never_overwrites(site, tmp_path, capsys):
    baseline = tmp_path / "base.json"
    assert run(site, baseline, "init") == 0
    assert "Recorded 4 file(s)" in capsys.readouterr().out
    assert run(site, baseline, "check") == 0
    assert "No changes - everything matches." in capsys.readouterr().out
    assert run(site, baseline, "init") == 1
    assert "already exists" in capsys.readouterr().out


def test_check_reports_every_kind_of_change(site, tmp_path, capsys):
    baseline = tmp_path / "base.json"
    run(site, baseline, "init")
    capsys.readouterr()
    (site / "index.html").write_text("<h1>defaced</h1>")
    (site / "app" / "main.py").unlink()
    (site / "evil.php").write_text("<?php evil();")
    assert run(site, baseline, "check") == 1
    out = capsys.readouterr().out
    assert "MODIFIED            index.html" in out and "ADDED               evil.php" in out
    assert "REMOVED             app/main.py" in out and "3 change(s) found." in out
    assert "2 unchanged" in out


def test_update_is_a_dry_run_until_apply_and_keeps_a_backup(site, tmp_path, capsys):
    baseline = tmp_path / "base.json"
    run(site, baseline, "init")
    original = baseline.read_text()
    (site / "index.html").write_text("<h1>new</h1>")
    capsys.readouterr()
    assert run(site, baseline, "update") == 0
    assert "Dry run" in capsys.readouterr().out and baseline.read_text() == original
    assert run(site, baseline, "update", "--apply") == 0
    backups = list(tmp_path.glob("base.json.*.prev"))
    assert len(backups) == 1 and backups[0].read_text() == original
    assert run(site, baseline, "check") == 0
    capsys.readouterr()
    assert run(site, baseline, "update", "--apply") == 0
    assert "already up to date" in capsys.readouterr().out


def test_signed_baselines_detect_tampering(site, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FIM_KEY", "s3cret")
    baseline = tmp_path / "base.json"
    assert run(site, baseline, "init", "--key-env", "FIM_KEY") == 0
    assert json.loads(baseline.read_text())["hmac"]
    capsys.readouterr()
    assert run(site, baseline, "check", "--key-env", "FIM_KEY") == 0
    data = json.loads(baseline.read_text())
    data["files"]["index.html"]["sha256"] = "0" * 64  # an attacker edits the baseline
    baseline.write_text(json.dumps(data))
    assert run(site, baseline, "check", "--key-env", "FIM_KEY") == 2
    assert "BASELINE TAMPERED" in capsys.readouterr().out
    assert run(site, baseline, "check") == 1  # without the key it only warns, then reports changes
    assert "baseline is signed" in capsys.readouterr().out


def test_bad_inputs(site, tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("NO_SUCH_KEY", raising=False)
    with pytest.raises(SystemExit):
        run(site, tmp_path / "b.json", "init", "--key-env", "NO_SUCH_KEY")
    with pytest.raises(SystemExit):
        run(tmp_path / "gone", tmp_path / "b.json", "check")
    assert run(site, tmp_path / "missing.json", "check") == 1
    bad = tmp_path / "bad.json"
    bad.write_text('{"nope": 1}')
    assert run(site, bad, "check") == 1
    assert "Couldn't read the baseline" in capsys.readouterr().err
