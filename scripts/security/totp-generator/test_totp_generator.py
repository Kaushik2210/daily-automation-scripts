import base64
import json

import pytest
import totp_generator as tg

SHA1_KEY = b"12345678901234567890"
SHA256_KEY = b"12345678901234567890123456789012"
SHA512_KEY = b"1234567890123456789012345678901234567890123456789012345678901234"


def test_hotp_matches_the_rfc_4226_test_vectors():
    expected = ["755224", "287082", "359152", "969429", "338314",
                "254676", "287922", "162583", "399871", "520489"]
    assert [tg.hotp(SHA1_KEY, counter) for counter in range(10)] == expected


@pytest.mark.parametrize("algorithm,key,table", [
    ("SHA1", SHA1_KEY, {59: "94287082", 1111111109: "07081804", 1111111111: "14050471",
                        1234567890: "89005924", 2000000000: "69279037",
                        20000000000: "65353130"}),
    ("SHA256", SHA256_KEY, {59: "46119246", 1111111109: "68084774", 1111111111: "67062674",
                            1234567890: "91819424", 2000000000: "90698825",
                            20000000000: "77737706"}),
    ("SHA512", SHA512_KEY, {59: "90693936", 1111111109: "25091201", 1111111111: "99943326",
                            1234567890: "93441116", 2000000000: "38618901",
                            20000000000: "47863826"})])
def test_totp_matches_the_rfc_6238_test_vectors(algorithm, key, table):
    for moment, code in table.items():
        assert tg.totp(key, moment, 30, 8, algorithm) == code


def test_six_digit_codes_are_the_tail_of_the_eight_digit_ones():
    assert tg.totp(SHA1_KEY, 59, 30, 6) == "287082"  # the same step as counter 1 above
    assert tg.totp(SHA1_KEY, 59, 30, 6) == "94287082"[-6:]


def test_clean_secret_accepts_common_formats():
    encoded = base64.b32encode(SHA1_KEY).decode()
    assert tg.clean_secret(encoded) == SHA1_KEY
    spaced = " ".join(encoded[i:i + 4] for i in range(0, len(encoded), 4)).lower()
    assert tg.clean_secret(spaced) == SHA1_KEY
    assert tg.clean_secret(encoded.rstrip("=")) == SHA1_KEY
    assert tg.clean_secret("jbsw-y3dp-ehpk-3pxp") == b"Hello!\xde\xad\xbe\xef"
    for bad in ("", "   ", "not base32!!", "1890"):
        with pytest.raises(ValueError):
            tg.clean_secret(bad)


def test_parse_uri():
    uri = ("otpauth://totp/Example%20Co:ada@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Example"
           "&algorithm=sha256&digits=8&period=60")
    settings = tg.parse_uri(uri)
    assert settings == {"secret": "JBSWY3DPEHPK3PXP", "digits": 8, "period": 60,
                        "algorithm": "SHA256", "label": "Example Co:ada@example.com",
                        "issuer": "Example"}
    assert tg.parse_uri("otpauth://totp/x?secret=ABC")["period"] == 30
    for bad in ("https://example.com", "otpauth://hotp/x?secret=ABC", "otpauth://totp/x",
                "otpauth://totp/x?secret=ABC&algorithm=md5"):
        with pytest.raises(ValueError):
            tg.parse_uri(bad)


def test_verify_window():
    key = SHA1_KEY
    now = 1_700_000_000
    current = tg.totp(key, now)
    assert tg.verify(key, current, now, 0, 30, 6, "SHA1")
    assert tg.verify(key, f"{current[:3]} {current[3:]}", now, 0, 30, 6, "SHA1")  # spaces are fine
    previous = tg.totp(key, now - 30)
    assert not tg.verify(key, previous, now, 0, 30, 6, "SHA1")
    assert tg.verify(key, previous, now, 1, 30, 6, "SHA1")
    assert not tg.verify(key, tg.totp(key, now - 90), now, 1, 30, 6, "SHA1")
    assert not tg.verify(key, "000000" if current != "000000" else "111111", now, 1, 30, 6, "SHA1")


def test_when_accepts_unix_and_iso():
    assert tg.when("1700000000") == 1700000000.0
    assert tg.when("2023-11-14T22:13:20+00:00") == 1700000000.0


def test_cli_output_and_json(tmp_path, capsys):
    secret = tmp_path / "s.txt"
    secret.write_text(base64.b32encode(SHA1_KEY).decode() + "\n")
    assert tg.main(["--secret-file", str(secret), "--time", "59", "--digits", "8"]) == 0
    assert capsys.readouterr().out == "9428 7082   (valid for 1 more second(s))\n"
    assert tg.main(["--secret-file", str(secret), "--time", "59", "--count", "3"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("287 082") and lines[1].endswith("(in 1 s)")
    assert lines[2].endswith("(in 31 s)")
    assert tg.main(["--secret-file", str(secret), "--time", "59", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["code"] == "287082" and data["valid_for_seconds"] == 1 and data["digits"] == 6


def test_cli_verify_exit_codes(tmp_path, capsys):
    secret = tmp_path / "s.txt"
    secret.write_text(base64.b32encode(SHA1_KEY).decode())
    base = ["--secret-file", str(secret), "--time", "59"]
    assert tg.main([*base, "--verify", "287082"]) == 0
    assert capsys.readouterr().out.strip() == "valid"
    assert tg.main([*base, "--verify", "123456"]) == 1
    assert capsys.readouterr().out.strip() == "invalid"


def test_cli_secret_sources_and_warnings(tmp_path, monkeypatch, capsys):
    encoded = base64.b32encode(SHA1_KEY).decode()
    assert tg.main(["--secret", encoded, "--time", "59"]) == 0
    captured = capsys.readouterr()
    assert captured.out.startswith("287 082") and "shell history" in captured.err
    monkeypatch.setenv("TOTP_SECRET", encoded)
    assert tg.main(["--time", "59"]) == 0
    assert "shell history" not in capsys.readouterr().err
    assert tg.main(["--uri", f"otpauth://totp/x?secret={encoded}&digits=8", "--time", "59"]) == 0
    assert capsys.readouterr().out.startswith("9428 7082")
    monkeypatch.delenv("TOTP_SECRET")
    assert tg.main(["--time", "59"]) == 1
    assert "give the secret" in capsys.readouterr().err
    assert tg.main(["--secret", "###", "--time", "59"]) == 1
    capsys.readouterr()
    assert tg.main(["--secret", "AAAA", "--time", "59"]) == 0
    assert "shorter than 80 bits" in capsys.readouterr().err


def test_cli_argument_errors():
    with pytest.raises(SystemExit):
        tg.main(["--secret", "AAAA", "--count", "0"])
    with pytest.raises(SystemExit):
        tg.main(["--secret", "AAAA", "--window", "-1"])
