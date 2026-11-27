import json

import note_vault as nv
import pytest

PASSPHRASE = "correct horse battery"


@pytest.fixture(autouse=True)
def fast_kdf(monkeypatch):
    monkeypatch.setattr(nv, "SCRYPT_LOG2", 10)  # real use is 2**15; tests don't need to wait


@pytest.fixture
def secret(tmp_path):
    path = tmp_path / "pass.txt"
    path.write_text(PASSPHRASE + "\n", encoding="utf-8")
    return str(path)


def run(tmp_path, secret, *argv):
    return nv.main([*argv, "--vault", str(tmp_path / "v.dat"), "--passphrase-file", secret])


def test_round_trip_and_ciphertext_is_random():
    blob = nv.encrypt(b"hello", PASSPHRASE)
    assert nv.decrypt(blob, PASSPHRASE) == b"hello"
    assert blob != nv.encrypt(b"hello", PASSPHRASE)  # fresh salt and nonce every time
    assert blob.startswith(b"DAS1") and b"hello" not in blob


def test_wrong_passphrase_tampering_and_bad_files():
    blob = nv.encrypt(b"hello", PASSPHRASE)
    with pytest.raises(ValueError, match="wrong passphrase"):
        nv.decrypt(blob, "not the passphrase")
    flipped = bytearray(blob)
    flipped[-1] ^= 1
    with pytest.raises(ValueError, match="wrong passphrase, or the file has been changed"):
        nv.decrypt(bytes(flipped), PASSPHRASE)
    header_change = bytearray(blob)
    header_change[30] ^= 1  # the header is authenticated too
    with pytest.raises(ValueError):
        nv.decrypt(bytes(header_change), PASSPHRASE)
    for bad in (b"", b"short", b"XXXX" + blob[4:]):
        with pytest.raises(ValueError, match="isn't an encrypted vault"):
            nv.decrypt(bad, PASSPHRASE)


def test_absurd_key_settings_are_refused():
    blob = bytearray(nv.encrypt(b"x", PASSPHRASE))
    blob[4] = 30  # would need terabytes of memory
    with pytest.raises(ValueError, match="unreasonable"):
        nv.decrypt(bytes(blob), PASSPHRASE)


def test_passphrase_sources(tmp_path, monkeypatch, secret):
    args = nv.argparse.Namespace(passphrase_file=None, passphrase_env="NV_TEST")
    monkeypatch.setenv("NV_TEST", "from the environment")
    assert nv.get_passphrase(args, creating=False) == "from the environment"
    monkeypatch.delenv("NV_TEST")
    typed = iter(["typed passphrase", "typed passphrase"])
    monkeypatch.setattr(nv.getpass, "getpass", lambda prompt="": next(typed))
    assert nv.get_passphrase(args, creating=True) == "typed passphrase"
    mismatch = iter(["first one here", "second one here"])
    monkeypatch.setattr(nv.getpass, "getpass", lambda prompt="": next(mismatch))
    with pytest.raises(ValueError, match="didn't match"):
        nv.get_passphrase(args, creating=True)
    from_file = nv.argparse.Namespace(passphrase_file=tmp_path / "pass.txt", passphrase_env="X")
    assert nv.get_passphrase(from_file, creating=False) == PASSPHRASE
    short = nv.argparse.Namespace(passphrase_file=None, passphrase_env="NV_SHORT")
    monkeypatch.setenv("NV_SHORT", "short")
    with pytest.raises(ValueError, match="at least 8"):
        nv.get_passphrase(short, creating=True)
    assert nv.get_passphrase(short, creating=False) == "short"  # opening isn't length-checked


def test_add_list_show_search_delete(tmp_path, secret, capsys):
    assert run(tmp_path, secret, "add", "Wifi", "--text", "router password is on the fridge") == 0
    assert run(tmp_path, secret, "add", "Recipe", "--text", "pancakes") == 0
    capsys.readouterr()
    assert run(tmp_path, secret, "list") == 0
    listing = capsys.readouterr().out
    assert "Recipe" in listing and "Wifi" in listing and "router password" not in listing
    assert run(tmp_path, secret, "show", "wifi") == 0  # titles are case-insensitive
    assert capsys.readouterr().out.strip() == "router password is on the fridge"
    assert run(tmp_path, secret, "search", "FRIDGE") == 0
    assert capsys.readouterr().out.strip() == "Wifi: router password is on the fridge"
    assert run(tmp_path, secret, "search", "nothing like this") == 0
    assert "No notes match." in capsys.readouterr().out
    assert run(tmp_path, secret, "delete", "Recipe") == 0
    assert "Add --yes" in capsys.readouterr().out
    assert run(tmp_path, secret, "show", "Recipe") == 0  # still there: that was a dry run
    capsys.readouterr()
    assert run(tmp_path, secret, "delete", "Recipe", "--yes") == 0
    assert "Deleted 'Recipe'" in capsys.readouterr().out
    assert run(tmp_path, secret, "show", "Recipe") == 1


def test_the_file_never_contains_the_notes_and_no_temp_files_remain(tmp_path, secret):
    run(tmp_path, secret, "add", "Secret title", "--text", "very secret words")
    raw = (tmp_path / "v.dat").read_bytes()
    assert b"very secret" not in raw and b"Secret title" not in raw
    assert sorted(p.name for p in tmp_path.iterdir()) == ["pass.txt", "v.dat"]


def test_duplicates_replace_and_file_input(tmp_path, secret, capsys):
    note = tmp_path / "note.txt"
    note.write_text("from a file", encoding="utf-8")
    assert run(tmp_path, secret, "add", "A", "--file", str(note)) == 0
    assert run(tmp_path, secret, "add", "a", "--text", "again") == 1
    assert "already exists" in capsys.readouterr().err
    assert run(tmp_path, secret, "add", "A", "--text", "newer", "--replace") == 0
    capsys.readouterr()
    run(tmp_path, secret, "show", "A")
    assert capsys.readouterr().out.strip() == "newer"


def test_wrong_passphrase_leaves_the_vault_untouched(tmp_path, secret, capsys):
    run(tmp_path, secret, "add", "A", "--text", "one")
    before = (tmp_path / "v.dat").read_bytes()
    other = tmp_path / "other.txt"
    other.write_text("a different passphrase\n")
    code = nv.main(["add", "B", "--text", "two", "--vault", str(tmp_path / "v.dat"),
                    "--passphrase-file", str(other)])
    assert code == 1 and "wrong passphrase" in capsys.readouterr().err
    assert (tmp_path / "v.dat").read_bytes() == before


def test_errors(tmp_path, secret, capsys):
    assert run(tmp_path, secret, "list") == 1
    assert "No vault at" in capsys.readouterr().err
    run(tmp_path, secret, "add", "A", "--text", "x")
    capsys.readouterr()
    assert run(tmp_path, secret, "show") == 1
    assert "needs a note title" in capsys.readouterr().err
    assert run(tmp_path, secret, "search") == 1
    garbage = tmp_path / "g.dat"
    garbage.write_bytes(b"not a vault at all, just some text that is long enough to try")
    assert nv.main(["list", "--vault", str(garbage), "--passphrase-file", secret]) == 1
    assert "isn't an encrypted vault" in capsys.readouterr().err


def test_a_vault_made_with_the_documented_format_opens(tmp_path):
    notes = {"notes": {"t": {"text": "x", "created": "c", "updated": "2026-01-01T00:00:00"}}}
    (tmp_path / "v.dat").write_bytes(nv.encrypt(json.dumps(notes).encode(), PASSPHRASE))
    assert json.loads(nv.decrypt((tmp_path / "v.dat").read_bytes(), PASSPHRASE)) == notes
