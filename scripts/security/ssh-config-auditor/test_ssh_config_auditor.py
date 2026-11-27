import json
import os
import stat

import pytest
import ssh_config_auditor as sca

CONFIG = """# demo
Host *
    ForwardAgent yes
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    Ciphers aes256-ctr,3des-cbc,arcfour
    MACs hmac-sha2-256,hmac-md5
    HostKeyAlgorithms +ssh-rsa
    Protocol 1,2

Host github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes

Host build-server
    HostName 10.0.4.12
    PasswordAuthentication yes
    ForwardX11 yes
    Compression yes
    HashKnownHosts no
    ForwardAgent yes
Include ~/.ssh/config.d/*
"""


def titles(findings):
    return [f["title"] for f in findings]


def test_parse_handles_contexts_equals_and_comments():
    directives = sca.parse("Port=22\nHost a b\n  ForwardAgent   yes  # not a comment here\n"
                           "# comment\n\nMatch user bob\n    PasswordAuthentication yes\n")
    assert [(d["key"], d["context"]) for d in directives] == [
        ("port", "global"), ("host", "Host a b"), ("forwardagent", "Host a b"),
        ("match", "Match user bob"), ("passwordauthentication", "Match user bob")]
    assert directives[0]["value"] == "22" and directives[0]["global"] is True
    assert directives[2]["global"] is False and directives[2]["line"] == 3


def test_client_audit_finds_the_risky_settings_with_the_right_severity():
    findings, includes = sca.audit(CONFIG)
    by_title = {f["title"]: f for f in findings}
    assert by_title["SSH protocol 1 is enabled"]["severity"] == "critical"
    assert by_title["host key checking is turned off"]["severity"] == "high"
    assert by_title["known hosts are thrown away"]["severity"] == "high"
    assert by_title["weak algorithm 3des-cbc in ciphers"]["severity"] == "high"
    assert by_title["weak algorithm arcfour in ciphers"]["severity"] == "high"
    assert by_title["weak algorithm hmac-md5 in macs"]["severity"] == "high"
    assert by_title["weak algorithm ssh-rsa in hostkeyalgorithms"]["line"] == 8
    assert includes == ["~/.ssh/config.d/*"]
    assert "weak algorithm aes256-ctr in ciphers" not in by_title  # CTR is fine
    assert [f["severity"] for f in findings] == sorted(
        (f["severity"] for f in findings), key=lambda s: -sca.LEVELS[s])  # worst first


def test_severity_depends_on_whether_the_setting_is_global():
    findings, _ = sca.audit(CONFIG)
    agent = [f for f in findings if f["title"].startswith("agent forwarding")]
    assert sorted((f["severity"], f["context"]) for f in agent) == [
        ("high", "Host *"), ("medium", "Host build-server")]
    passwords = next(f for f in findings if f["title"].startswith("password login"))
    assert passwords["severity"] == "low" and passwords["context"] == "Host build-server"


def test_removing_a_weak_algorithm_is_not_flagged():
    findings, _ = sca.audit("Host *\n    Ciphers -3des-cbc,aes256-gcm@openssh.com\n")
    assert findings == []
    assert sca.audit("Ciphers +3des-cbc\n")[0][0]["severity"] == "high"


def test_safe_config_has_no_findings():
    safe = ("Host *\n    HashKnownHosts yes\n    StrictHostKeyChecking accept-new\n"
            "    Ciphers aes256-gcm@openssh.com,chacha20-poly1305@openssh.com\n"
            "    PasswordAuthentication no\n    ForwardAgent no\n")
    assert sca.audit(safe)[0] == []


def test_server_mode():
    text = ("PermitRootLogin yes\nPermitEmptyPasswords yes\nPasswordAuthentication yes\n"
            "PubkeyAuthentication no\nMaxAuthTries 10\nLoginGraceTime 300\nX11Forwarding yes\n"
            "StrictModes no\nPermitRootLogin prohibit-password\nProtocol 2,1\n")
    findings, _ = sca.audit(text, server=True)
    got = {f["title"]: f["severity"] for f in findings}
    assert got["root can log in over SSH"] == "high"
    assert got["accounts with empty passwords can log in"] == "critical"
    assert got["SSH protocol 1 is enabled"] == "critical"
    assert got["strictmodes is off"] == "high"
    assert got["10 login attempts per connection"] == "low"
    assert "agent forwarding is on applies to every host" not in got  # client-only rule
    assert sca.audit("PermitRootLogin prohibit-password\n", server=True)[0] == []


@pytest.mark.skipif(os.name == "nt", reason="file permission bits don't apply on Windows")
def test_identity_file_permissions(tmp_path):
    key = tmp_path / "id_test"
    key.write_text("not a real key")
    key.chmod(0o644)
    config = f"Host a\n    IdentityFile {key}\n"
    assert sca.audit(config, check_files=True)[0][0]["title"].endswith("is readable by other users")
    key.chmod(0o600)
    assert sca.audit(config, check_files=True)[0] == []
    assert sca.audit(config, check_files=False)[0] == []
    assert sca.audit("Host a\n    IdentityFile %d/id\n", check_files=True)[0] == []
    assert stat.S_IMODE(key.stat().st_mode) == 0o600


def test_missing_identity_files_are_ignored(tmp_path):
    assert sca.audit(f"IdentityFile {tmp_path}/nothing\n", check_files=True)[0] == []


def test_cli_text_filters_and_exit_codes(tmp_path, capsys):
    path = tmp_path / "config"
    path.write_text(CONFIG, encoding="utf-8")
    assert sca.main([str(path)]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].endswith("finding(s)") and "[CRITICAL] line 9 (Host *)" in out
    assert "Not followed: Include ~/.ssh/config.d/*" in out
    assert sca.main([str(path), "--min-severity", "critical"]) == 0
    assert capsys.readouterr().out.count("[") == 1
    assert sca.main([str(path), "--fail-on", "high"]) == 1
    capsys.readouterr()
    assert sca.main([str(path), "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["includes_not_followed"] == ["~/.ssh/config.d/*"] and data["findings"]


def test_cli_clean_and_missing_files(tmp_path, capsys):
    clean = tmp_path / "clean"
    clean.write_text("Host *\n    PasswordAuthentication no\n")
    assert sca.main([str(clean), "--fail-on", "medium"]) == 0
    assert "Nothing risky found" in capsys.readouterr().out
    assert sca.main([str(tmp_path / "missing")]) == 1
    assert "Can't read" in capsys.readouterr().err
