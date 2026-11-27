import json
import os
import shutil
import subprocess

import pytest
import signature_verifier as sv

FPR = "0123456789ABCDEF0123456789ABCDEF01234567"
GOOD = (
    "[GNUPG:] NEWSIG\n[GNUPG:] KEY_CONSIDERED " + FPR + " 0\n"
    "[GNUPG:] GOODSIG 89ABCDEF01234567 Ada Lovelace <ada@example.com>\n"
    "[GNUPG:] VALIDSIG " + FPR + " 2026-11-20 1763971200 0 4 0 1 10 00 " + FPR + "\n"
    "[GNUPG:] TRUST_FULLY 0 pgp\n")
BAD = "[GNUPG:] NEWSIG\n[GNUPG:] BADSIG 89ABCDEF01234567 Ada Lovelace <ada@example.com>\n"
NOKEY = ("[GNUPG:] NEWSIG\n[GNUPG:] ERRSIG 89ABCDEF01234567 22 8 00 1763971200 9 -\n"
         "[GNUPG:] NO_PUBKEY 89ABCDEF01234567\n")
HAVE_GPG = shutil.which("gpg") is not None


def test_parse_good_signature():
    result = sv.parse_status(GOOD)
    assert result["verdict"] == "good" and result["key_id"] == "89ABCDEF01234567"
    assert result["signer"] == "Ada Lovelace <ada@example.com>"
    assert result["fingerprint"] == FPR and result["primary_fingerprint"] == FPR
    assert result["signed_on"] == "2025-11-24" and result["trust"] == "fully"


def test_parse_other_outcomes():
    assert sv.parse_status(BAD)["verdict"] == "bad"
    unknown = sv.parse_status(NOKEY)
    assert unknown["verdict"] == "unknown_key" and unknown["key_id"] == "89ABCDEF01234567"
    assert unknown["signer"] is None  # ERRSIG's other fields aren't a name
    assert sv.parse_status("")["verdict"] == "none"
    assert sv.parse_status("gpg: Good signature from nobody\n")["verdict"] == "none"  # not status
    for word, verdict in (("EXPKEYSIG", "expired_key"), ("EXPSIG", "expired_signature"),
                          ("REVKEYSIG", "revoked_key")):
        assert sv.parse_status(f"[GNUPG:] {word} ABCD1234 Someone <s@example.com>\n")[
            "verdict"] == verdict


def test_the_worst_signature_wins_in_either_order():
    assert sv.parse_status(GOOD + BAD)["verdict"] == "bad"
    assert sv.parse_status(BAD + GOOD)["verdict"] == "bad"
    mixed = sv.parse_status(GOOD + NOKEY)
    assert mixed["verdict"] == "unknown_key" and mixed["fingerprint"] is None
    assert sv.judge(mixed, [], None)[0] is False
    assert sv.parse_status("gpg: Good signature\n" + BAD)["verdict"] == "bad"


def test_judge_requirements():
    result = sv.parse_status(GOOD)
    assert sv.judge(result, [], None) == (True, [])
    assert sv.judge(result, [FPR.lower()], None)[0] is True
    ok, reasons = sv.judge(result, ["AAAA" * 10], None)
    assert not ok and "not one of the fingerprints" in reasons[0]
    assert sv.judge(result, [], "full")[0] and not sv.judge(result, [], "ultimate")[0]
    undefined = {**result, "trust": None}
    assert not sv.judge(undefined, [], "marginal")[0]
    assert sv.judge(sv.parse_status(BAD), [], None)[1] == [sv.WORDS["bad"]]


def test_space_groups_fingerprints():
    assert sv.space("ABCD1234EF") == "ABCD 1234 EF"


def test_cli_from_saved_status(tmp_path, capsys):
    saved = tmp_path / "s.txt"
    saved.write_text(GOOD)
    assert sv.main(["--from-status", str(saved)]) == 0
    out = capsys.readouterr().out
    assert "Signature: GOOD" in out and "Signer:      Ada Lovelace" in out
    assert "0123 4567 89AB CDEF" in out and "Signed on:   2025-11-24" in out
    assert "Key trust:   fully" in out and "Accepted." in out
    assert sv.main(["--from-status", str(saved), "--expect-fingerprint", "FFFF"]) == 1
    assert "Rejected: the signing key is not one of" in capsys.readouterr().out
    assert sv.main(["--from-status", str(saved), "--require-trust", "ultimate", "--format",
                    "json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["accepted"] is False and data["verdict"] == "good" and data["problems"]


def test_cli_bad_and_unknown_signatures(tmp_path, capsys):
    saved = tmp_path / "s.txt"
    saved.write_text(BAD)
    assert sv.main(["--from-status", str(saved)]) == 1
    assert "Signature: BAD" in capsys.readouterr().out
    saved.write_text(NOKEY)
    assert sv.main(["--from-status", str(saved)]) == 1
    assert "public key isn't in your keyring" in capsys.readouterr().out
    saved.write_text("")
    assert sv.main(["--from-status", str(saved)]) == 1
    assert "NO SIGNATURE FOUND" in capsys.readouterr().out


def test_cli_untrusted_good_signature_gets_a_warning(tmp_path, capsys):
    saved = tmp_path / "s.txt"
    saved.write_text(GOOD.replace("TRUST_FULLY", "TRUST_UNDEFINED"))
    assert sv.main(["--from-status", str(saved)]) == 0
    assert "isn't certified" in capsys.readouterr().out


def test_cli_errors(tmp_path, capsys):
    assert sv.main(["--from-status", str(tmp_path / "none.txt")]) == 1
    with pytest.raises(SystemExit):
        sv.main([])
    assert sv.main([str(tmp_path / "a.sig"), "--gpg", "definitely-not-installed-gpg"]) == 1
    assert "Can't find" in capsys.readouterr().err
    if HAVE_GPG:
        assert sv.main([str(tmp_path / "missing.sig")]) == 1
        assert "Not a file" in capsys.readouterr().err


@pytest.mark.skipif(not HAVE_GPG, reason="gpg is not installed")
@pytest.mark.skipif(os.name == "nt", reason="Windows paths confuse the gpg-agent of MSYS builds")
def test_real_gnupg_good_bad_and_unknown_key(tmp_path, capsys):
    home = tmp_path / "gnupg"
    home.mkdir()
    gpg = ["gpg", "--homedir", str(home), "--batch", "--no-tty", "--pinentry-mode", "loopback",
           "--passphrase", ""]
    made = subprocess.run([*gpg, "--quick-generate-key", "Test Signer <test@example.com>",
                           "ed25519", "sign", "never"], capture_output=True, text=True, timeout=120)
    if made.returncode:
        pytest.skip(f"gpg can't make a key here: {made.stderr.strip()[-80:]}")
    data = tmp_path / "release.txt"
    data.write_bytes(b"version 1.0\n")
    subprocess.run([*gpg, "--detach-sign", "--armor", str(data)], check=True, timeout=60)
    signature = tmp_path / "release.txt.asc"

    assert sv.main([str(signature), str(data), "--homedir", str(home)]) == 0
    out = capsys.readouterr().out
    assert "Signature: GOOD" in out and "Test Signer" in out and "Accepted." in out
    listing = subprocess.run([*gpg, "--with-colons", "--fingerprint"], capture_output=True,
                             text=True, timeout=60).stdout
    fingerprint = next(line.split(":")[9] for line in listing.splitlines()
                       if line.startswith("fpr:"))
    assert sv.main([str(signature), str(data), "--homedir", str(home),
                    "--expect-fingerprint", fingerprint]) == 0
    assert sv.main([str(signature), str(data), "--homedir", str(home),
                    "--expect-fingerprint", "A" * 40]) == 1
    capsys.readouterr()

    data.write_bytes(b"version 1.0 -- tampered\n")
    assert sv.main([str(signature), str(data), "--homedir", str(home)]) == 1
    assert "Signature: BAD" in capsys.readouterr().out

    data.write_bytes(b"version 1.0\n")
    empty = tmp_path / "empty-home"
    empty.mkdir()
    assert sv.main([str(signature), str(data), "--homedir", str(empty)]) == 1
    assert "public key isn't in your keyring" in capsys.readouterr().out
