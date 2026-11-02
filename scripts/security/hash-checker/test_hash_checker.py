import hashlib

import pytest
from hash_checker import clean_expected, file_digest, guess_algorithm, main, matches

DATA = b"hello world"
SHA256 = hashlib.sha256(DATA).hexdigest()


def test_file_digest(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(DATA)
    assert file_digest(f, "sha256") == SHA256
    assert file_digest(f, "md5") == hashlib.md5(DATA).hexdigest()


def test_clean_expected_formats():
    assert clean_expected(f"  {SHA256.upper()}  ") == SHA256
    assert clean_expected(f"{SHA256}  file.iso") == SHA256
    assert clean_expected(f"SHA256:{SHA256}") == SHA256


def test_guess_algorithm_and_matches():
    assert guess_algorithm("a" * 32) == "md5" and guess_algorithm("a" * 64) == "sha256"
    assert guess_algorithm("abc") is None
    assert matches("ABCDEF", "abcdef") and not matches("a", "b")


def test_cli_ok_mismatch_and_checksum_file(tmp_path, capsys):
    f = tmp_path / "a.bin"
    f.write_bytes(DATA)
    assert main([str(f), SHA256]) == 0
    assert "OK" in capsys.readouterr().out
    assert main([str(f), "0" * 64]) == 1
    assert "MISMATCH" in capsys.readouterr().out
    sums = tmp_path / "a.sha256"
    sums.write_text(f"{SHA256}  a.bin\n")
    assert main([str(f), str(sums)]) == 0


def test_unknown_length_is_an_error(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(DATA)
    with pytest.raises(SystemExit):
        main([str(f), "abc123"])
