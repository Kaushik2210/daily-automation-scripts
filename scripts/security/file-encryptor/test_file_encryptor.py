import file_encryptor as fe
import pytest

PASSPHRASE = "correct horse battery"


@pytest.fixture(autouse=True)
def fast_kdf(monkeypatch):
    monkeypatch.setattr(fe, "SCRYPT_LOG2", 10)


@pytest.fixture
def secret(tmp_path):
    path = tmp_path / "pass.txt"
    path.write_text(PASSPHRASE + "\n", encoding="utf-8")
    return ["--passphrase-file", str(path)]


def test_crypto_round_trip_and_failures():
    blob = fe.encrypt(b"data", PASSPHRASE)
    assert fe.decrypt(blob, PASSPHRASE) == b"data" and b"data" not in blob
    with pytest.raises(ValueError, match="wrong passphrase"):
        fe.decrypt(blob, "nope")
    with pytest.raises(ValueError, match="isn't a file made by this tool"):
        fe.decrypt(b"plain text that is long enough to look like a file of some kind", PASSPHRASE)
    bad = bytearray(blob)
    bad[4] = 31
    with pytest.raises(ValueError, match="unreasonable"):
        fe.decrypt(bytes(bad), PASSPHRASE)


def test_target_names(tmp_path):
    assert fe.target_for(tmp_path / "a.txt", "encrypt", None) == tmp_path / "a.txt.enc"
    assert fe.target_for(tmp_path / "a.txt.enc", "decrypt", None) == tmp_path / "a.txt"
    assert fe.target_for(tmp_path / "a.bin", "decrypt", None) == tmp_path / "a.bin.decrypted"
    assert fe.target_for(tmp_path / "A.ENC", "decrypt", tmp_path / "out") == tmp_path / "out" / "A"


def test_encrypt_then_decrypt_files(tmp_path, secret, capsys):
    text = tmp_path / "notes.txt"
    binary = tmp_path / "pic.bin"
    empty = tmp_path / "empty.txt"
    text.write_text("hello world", encoding="utf-8")
    binary.write_bytes(bytes(range(256)) * 10)
    empty.write_bytes(b"")
    assert fe.main(["encrypt", str(text), str(binary), str(empty), *secret]) == 0
    assert "3 of 3 file(s) encrypted" in capsys.readouterr().out
    assert b"hello world" not in (tmp_path / "notes.txt.enc").read_bytes()
    out = tmp_path / "restored"
    out.mkdir()
    encrypted = [str(tmp_path / f"{n}.enc") for n in ("notes.txt", "pic.bin", "empty.txt")]
    assert fe.main(["decrypt", *encrypted, "--output-dir", str(out), *secret]) == 0
    assert (out / "notes.txt").read_text(encoding="utf-8") == "hello world"
    assert (out / "pic.bin").read_bytes() == bytes(range(256)) * 10
    assert (out / "empty.txt").read_bytes() == b""
    assert text.exists()  # originals untouched


def test_never_overwrites(tmp_path, secret, capsys):
    source = tmp_path / "a.txt"
    source.write_text("one", encoding="utf-8")
    existing = tmp_path / "a.txt.enc"
    existing.write_bytes(b"precious")
    assert fe.main(["encrypt", str(source), *secret]) == 1
    assert "already exists; it was left alone" in capsys.readouterr().err
    assert existing.read_bytes() == b"precious"


def test_wrong_passphrase_writes_nothing(tmp_path, secret, capsys):
    source = tmp_path / "a.txt"
    source.write_text("one", encoding="utf-8")
    fe.main(["encrypt", str(source), *secret])
    other = tmp_path / "other.txt"
    other.write_text("a totally different phrase\n")
    out = tmp_path / "out"
    out.mkdir()
    code = fe.main(["decrypt", str(tmp_path / "a.txt.enc"), "--output-dir", str(out),
                    "--passphrase-file", str(other)])
    assert code == 1 and "wrong passphrase" in capsys.readouterr().err
    assert list(out.iterdir()) == []


def test_remove_original_is_a_preview_until_apply(tmp_path, secret, capsys):
    source = tmp_path / "a.txt"
    source.write_text("keep me safe", encoding="utf-8")
    assert fe.main(["encrypt", str(source), "--remove-original", *secret]) == 0
    assert "would remove" in capsys.readouterr().out and source.exists()
    (tmp_path / "a.txt.enc").unlink()
    assert fe.main(["encrypt", str(source), "--remove-original", "--apply", *secret]) == 0
    assert "removed" in capsys.readouterr().out and not source.exists()
    restored = tmp_path / "back"
    restored.mkdir()
    assert fe.main(["decrypt", str(tmp_path / "a.txt.enc"), "--output-dir", str(restored),
                    *secret]) == 0
    assert (restored / "a.txt").read_text(encoding="utf-8") == "keep me safe"


def test_skips_and_reports_problems_but_continues(tmp_path, secret, capsys):
    good = tmp_path / "good.txt"
    good.write_text("fine", encoding="utf-8")
    folder = tmp_path / "folder"
    folder.mkdir()
    big = tmp_path / "big.bin"
    big.write_bytes(b"x" * (2 * 1024 * 1024))
    code = fe.main(["encrypt", str(tmp_path / "missing.txt"), str(folder), str(big), str(good),
                    "--max-mb", "1", *secret])
    err = capsys.readouterr()
    assert code == 1 and "1 of 4 file(s) encrypted" in err.out
    assert "not a file" in err.err and "larger than 1 MB" in err.err
    assert (tmp_path / "good.txt.enc").exists()
    assert fe.main(["encrypt", str(tmp_path / "good.txt.enc"), *secret]) == 1
    assert "already encrypted" in capsys.readouterr().err


def test_passphrase_rules(tmp_path, monkeypatch, capsys):
    source = tmp_path / "a.txt"
    source.write_text("x")
    monkeypatch.setenv("FE_PW", "short")
    assert fe.main(["encrypt", str(source), "--passphrase-env", "FE_PW"]) == 1
    assert "at least 8" in capsys.readouterr().err
    empty = tmp_path / "empty.txt"
    empty.write_text("")
    assert fe.main(["encrypt", str(source), "--passphrase-file", str(empty)]) == 1
    with pytest.raises(SystemExit):
        fe.main(["encrypt", str(source), "--max-mb", "0"])
    with pytest.raises(SystemExit):
        fe.main(["encrypt", str(source), "--output-dir", str(tmp_path / "nope")])
