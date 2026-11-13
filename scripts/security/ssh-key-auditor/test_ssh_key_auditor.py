import base64
import hashlib
import os
import struct
import time

import pytest
import ssh_key_auditor as ska


def string(data):
    return struct.pack(">I", len(data)) + data


def mpint(number):
    data = number.to_bytes((number.bit_length() + 8) // 8, "big")
    return string(data)


def public_key(kind, bits=None, comment="me@laptop", options=""):
    if kind == "ssh-rsa":
        blob = string(b"ssh-rsa") + mpint(65537) + mpint(2 ** (bits - 1) + 1)
    elif kind == "ssh-dss":
        blob = string(b"ssh-dss") + mpint(2 ** (bits - 1) + 1) + mpint(7) + mpint(5) + mpint(9)
    elif kind.startswith("ecdsa"):
        blob = string(kind.encode()) + string(kind.split("-")[-1].encode()) + string(b"\x04" * 65)
    else:
        blob = string(kind.encode()) + string(b"\x01" * 32)
    line = f"{kind} {base64.b64encode(blob).decode()} {comment}"
    return (options + " " + line).strip(), blob


def test_parse_rsa_keys_measure_the_real_bit_length():
    line, blob = public_key("ssh-rsa", 4096)
    key = ska.parse_public_key(line)
    assert (key["type"], key["bits"], key["comment"]) == ("ssh-rsa", 4096, "me@laptop")
    expected = base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip("=")
    assert key["fingerprint"] == f"SHA256:{expected}"
    assert ska.parse_public_key(public_key("ssh-rsa", 2048)[0])["bits"] == 2048


@pytest.mark.parametrize("kind,bits", [
    ("ssh-ed25519", 256), ("ecdsa-sha2-nistp256", 256), ("ecdsa-sha2-nistp521", 521),
    ("sk-ssh-ed25519@openssh.com", 256), ("ssh-dss", 1024)])
def test_other_key_types(kind, bits):
    key = ska.parse_public_key(public_key(kind, bits)[0])
    assert key["type"] == kind and key["bits"] == bits


def test_authorized_keys_options_and_garbage():
    line, _ = public_key("ssh-ed25519", comment="deploy key",
                         options='command="/usr/bin/backup --all",no-pty')
    key = ska.parse_public_key(line)
    assert key["comment"] == "deploy key"
    assert key["options"] == 'command="/usr/bin/backup --all",no-pty'
    for bad in ("", "just some text", "ssh-rsa not-base64!!", "ssh-rsa AAAA", "ssh-ed25519"):
        assert ska.parse_public_key(bad) is None


@pytest.mark.parametrize("kind,bits,verdict", [
    ("ssh-dss", 1024, "WEAK"), ("ssh-rsa", 1024, "WEAK"), ("ssh-rsa", 2048, "NOTE"),
    ("ssh-rsa", 3072, "OK"), ("ssh-rsa", 4096, "OK"), ("ssh-ed25519", 256, "OK"),
    ("ecdsa-sha2-nistp256", 256, "OK"), ("sk-ssh-ed25519@openssh.com", 256, "OK")])
def test_judge_key(kind, bits, verdict):
    assert ska.judge_key({"type": kind, "bits": bits})[0] == verdict


def openssh_private(cipher):
    raw = b"openssh-key-v1\x00" + string(cipher) + string(b"none") + b"\x00" * 20
    body = base64.b64encode(raw).decode()
    return ("-----BEGIN OPENSSH PRIVATE KEY-----\n" + body[:70] + "\n" + body[70:]
            + "\n-----END OPENSSH PRIVATE KEY-----\n")


def test_private_key_encryption_detection():
    assert ska.private_key_state(openssh_private(b"none")) == "unencrypted"
    assert ska.private_key_state(openssh_private(b"aes256-ctr")) == "encrypted"
    assert ska.private_key_state("-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n") == "unencrypted"
    assert ska.private_key_state("-----BEGIN RSA PRIVATE KEY-----\nProc-Type: 4,ENCRYPTED\n") == (
        "encrypted")
    assert ska.private_key_state("-----BEGIN ENCRYPTED PRIVATE KEY-----\nabc\n") == "encrypted"
    assert ska.private_key_state("ssh-rsa AAAA... comment") is None
    assert ska.private_key_state("") is None
    assert ska.private_key_state("-----BEGIN OPENSSH PRIVATE KEY-----\n!!!!\n") is None


def test_audit_a_public_key_file_and_a_private_one(tmp_path):
    pub = tmp_path / "id_rsa.pub"
    pub.write_text(public_key("ssh-rsa", 2048)[0] + "\n")
    findings = ska.audit_path(pub)
    assert findings[0][0] == "NOTE" and "RSA 2048-bit" in findings[0][1]
    private = tmp_path / "id_ed25519"
    private.write_text(openssh_private(b"none"))
    os.chmod(private, 0o600)
    verdicts = [v for v, _ in ska.audit_path(private)]
    assert verdicts == ["WEAK"]


@pytest.mark.skipif(os.name != "posix", reason="permission bits only matter on Linux and macOS")
def test_open_permissions_on_a_private_key(tmp_path):
    private = tmp_path / "id_rsa"
    private.write_text(openssh_private(b"aes256-ctr"))
    os.chmod(private, 0o644)
    findings = ska.audit_path(private)
    assert ("OK", "private key is passphrase-protected") in findings
    assert any(v == "WEAK" and "chmod 600" in text for v, text in findings)


def test_age_note_and_skipped_lines(tmp_path):
    keys = tmp_path / "authorized_keys"
    keys.write_text("# comment\n" + public_key("ssh-ed25519")[0] + "\ngarbage line\n")
    old = time.time() - 400 * 86400
    os.utime(keys, (old, old))
    findings = ska.audit_path(keys, max_age_days=365)
    assert [v for v, _ in findings] == ["OK", "NOTE", "NOTE"]
    assert "400 days ago" in findings[-1][1]
    assert not any("days ago" in text for _, text in ska.audit_path(keys))


def test_cli_scans_a_folder_and_sets_the_exit_code(tmp_path, capsys):
    (tmp_path / "good.pub").write_text(public_key("ssh-ed25519")[0] + "\n")
    (tmp_path / "known_hosts").write_text("example.com ssh-rsa AAAA\n")
    assert ska.main([str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "good.pub" in out and "known_hosts" not in out and "0 weak" in out
    (tmp_path / "old.pub").write_text(public_key("ssh-dss", 1024)[0] + "\n")
    assert ska.main([str(tmp_path)]) == 1
    assert "[WEAK]" in capsys.readouterr().out


def test_no_keys_and_bad_paths(tmp_path, capsys):
    (tmp_path / "notes.txt").write_text("nothing here")
    assert ska.main([str(tmp_path)]) == 1
    assert "No SSH keys found." in capsys.readouterr().out
    explicit = tmp_path / "notes.txt"  # a file named on the command line is always examined
    assert ska.main([str(explicit)]) == 0
    assert "isn't a valid public key" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        ska.main([str(tmp_path / "gone")])
