import string

import password_vault as pv
import pytest

PASSPHRASE = "vault passphrase 1"


@pytest.fixture(autouse=True)
def fast_kdf(monkeypatch):
    monkeypatch.setattr(pv, "SCRYPT_LOG2", 10)


@pytest.fixture
def secret(tmp_path):
    path = tmp_path / "pass.txt"
    path.write_text(PASSPHRASE + "\n", encoding="utf-8")
    return str(path)


def run(tmp_path, secret, *argv):
    return pv.main([*argv, "--vault", str(tmp_path / "v.dat"), "--passphrase-file", secret])


def add(tmp_path, secret, name, password, *extra):
    entry = tmp_path / "entry.txt"
    entry.write_text(password + "\n", encoding="utf-8")
    return run(tmp_path, secret, "add", name, "--password-file", str(entry), *extra)


def test_round_trip_and_bad_input():
    blob = pv.encrypt(b"{}", PASSPHRASE)
    assert pv.decrypt(blob, PASSPHRASE) == b"{}"
    with pytest.raises(ValueError, match="wrong passphrase"):
        pv.decrypt(blob, "other passphrase")
    with pytest.raises(ValueError, match="isn't an encrypted vault"):
        pv.decrypt(b"x" * 80, PASSPHRASE)


@pytest.mark.parametrize("length,symbols", [(8, True), (20, True), (32, False), (12, True)])
def test_generate_always_has_every_character_class(length, symbols):
    for _ in range(30):
        text = pv.generate(length, symbols)
        assert len(text) == length
        assert any(c in string.ascii_lowercase for c in text)
        assert any(c in string.ascii_uppercase for c in text)
        assert any(c in string.digits for c in text)
        assert any(c in pv.SYMBOLS for c in text) is symbols
    with pytest.raises(ValueError):
        pv.generate(7)
    assert pv.generate(20) != pv.generate(20)


def test_read_secret_sources(tmp_path, monkeypatch):
    monkeypatch.setenv("PV_TEST", "from env")
    assert pv.read_secret(None, "PV_TEST", "p") == "from env"
    monkeypatch.delenv("PV_TEST")
    answers = iter(["typed", "typed"])
    monkeypatch.setattr(pv.getpass, "getpass", lambda prompt="": next(answers))
    assert pv.read_secret(None, "PV_TEST", "p", confirm=True) == "typed"
    answers = iter(["one", "two"])
    monkeypatch.setattr(pv.getpass, "getpass", lambda prompt="": next(answers))
    with pytest.raises(ValueError, match="didn't match"):
        pv.read_secret(None, None, "p", confirm=True)
    empty = tmp_path / "empty.txt"
    empty.write_text("")
    with pytest.raises(ValueError, match="empty"):
        pv.read_secret(empty, None, "p")


def test_add_get_list_delete(tmp_path, secret, capsys):
    assert add(tmp_path, secret, "GitHub", "s3cret-Value!", "--username", "ada",
               "--url", "https://github.com", "--notes", "personal") == 0
    assert add(tmp_path, secret, "email", "another-one-9") == 0
    capsys.readouterr()
    assert run(tmp_path, secret, "get", "github") == 0
    out = capsys.readouterr().out
    assert "Username:  ada" in out and "URL:       https://github.com" in out
    assert "s3cret-Value!" not in out and "(add --show)" in out  # masked by default
    assert run(tmp_path, secret, "get", "GITHUB", "--show") == 0
    assert "Password:  s3cret-Value!" in capsys.readouterr().out
    assert run(tmp_path, secret, "get", "github", "--password-only") == 0
    assert capsys.readouterr().out == "s3cret-Value!\n"
    assert run(tmp_path, secret, "list") == 0
    listing = capsys.readouterr().out
    assert "GitHub" in listing and "email" in listing and "s3cret" not in listing
    assert run(tmp_path, secret, "delete", "email") == 0
    assert "Add --yes" in capsys.readouterr().out
    assert run(tmp_path, secret, "delete", "email", "--yes") == 0
    assert run(tmp_path, secret, "get", "email") == 1


def test_generated_passwords_are_stored_and_shown_once(tmp_path, secret, capsys):
    assert run(tmp_path, secret, "add", "wifi", "--generate", "24", "--no-symbols") == 0
    shown = capsys.readouterr().out.split("Generated password: ")[1].strip()
    assert len(shown) == 24 and shown.isalnum()
    assert run(tmp_path, secret, "get", "wifi", "--password-only") == 0
    assert capsys.readouterr().out.strip() == shown


def test_generate_command_needs_no_vault(capsys):
    assert pv.main(["generate", "--length", "16"]) == 0
    assert len(capsys.readouterr().out.strip()) == 16
    with pytest.raises(SystemExit):
        pv.main(["generate", "--length", "4"])


def test_vault_file_hides_everything(tmp_path, secret):
    add(tmp_path, secret, "my-bank-login", "SuperSecret-Pass1", "--username", "ada.l")
    raw = (tmp_path / "v.dat").read_bytes()
    for text in (b"my-bank-login", b"SuperSecret", b"ada.l", b"password", b"entries"):
        assert text not in raw
    assert sorted(p.name for p in tmp_path.iterdir()) == ["entry.txt", "pass.txt", "v.dat"]


def test_replace_and_duplicates(tmp_path, secret, capsys):
    add(tmp_path, secret, "site", "first-password-1")
    assert add(tmp_path, secret, "SITE", "second-password-2") == 1
    assert "already exists" in capsys.readouterr().err
    assert add(tmp_path, secret, "site", "second-password-2", "--replace") == 0
    capsys.readouterr()
    run(tmp_path, secret, "get", "site", "--password-only")
    assert capsys.readouterr().out.strip() == "second-password-2"


def test_stale_entries_are_flagged(tmp_path, secret, capsys):
    add(tmp_path, secret, "old", "some-password-3")
    capsys.readouterr()
    run(tmp_path, secret, "list", "--stale-days", "-1")
    assert "not changed for 0 days" in capsys.readouterr().out


def test_wrong_vault_passphrase_and_missing_vault(tmp_path, secret, capsys):
    add(tmp_path, secret, "site", "some-password-4")
    other = tmp_path / "other.txt"
    other.write_text("completely different\n")
    capsys.readouterr()
    vault = str(tmp_path / "v.dat")
    assert pv.main(["list", "--vault", vault, "--passphrase-file", str(other)]) == 1
    assert "wrong passphrase" in capsys.readouterr().err
    missing = str(tmp_path / "none.dat")
    assert pv.main(["list", "--vault", missing, "--passphrase-file", secret]) == 1
    assert "No vault at" in capsys.readouterr().err
    assert run(tmp_path, secret, "get") == 1
    assert "needs an entry name" in capsys.readouterr().err
