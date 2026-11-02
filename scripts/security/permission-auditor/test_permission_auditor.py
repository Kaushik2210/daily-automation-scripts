import os
import stat

import pytest
from permission_auditor import audit, classify, main


def kinds(mode, is_dir=False, name="file.txt"):
    return [problem for problem, _ in classify(mode, is_dir, name)]


def test_world_writable_file_and_safer_mode():
    result = classify(0o666, False, "a.txt")
    assert result == [("world-writable file", 0o664)]
    assert kinds(0o644) == []


def test_folder_rules_sticky_bit():
    assert kinds(0o777, True, "d") == ["world-writable folder without sticky bit"]
    assert kinds(0o1777, True, "tmp") == []


def test_setuid_and_private_keys():
    assert "setuid/setgid file" in kinds(stat.S_ISUID | 0o755)
    assert kinds(0o644, name="id_rsa") == ["private key readable by others"]
    assert classify(0o644, False, "server.PEM")[0][1] == 0o600
    assert kinds(0o600, name="id_rsa") == []


def test_cli_on_windows_is_a_noop(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(os, "name", "nt")
    assert main([str(tmp_path)]) == 0
    assert "don't apply on Windows" in capsys.readouterr().out


@pytest.mark.skipif(os.name == "nt", reason="needs Unix permission bits")
def test_audit_dry_run_then_apply(tmp_path):
    f = tmp_path / "open.txt"
    f.write_text("x")
    f.chmod(0o666)
    assert [p.name for p, *_ in audit(tmp_path)] == ["open.txt"]
    main([str(tmp_path)])
    assert stat.S_IMODE(f.stat().st_mode) == 0o666
    main([str(tmp_path), "--apply"])
    assert stat.S_IMODE(f.stat().st_mode) == 0o664
