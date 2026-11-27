import base64
import hashlib
import hmac
import json

import jwt_decoder as jd
import pytest


def b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def make(header, payload, secret="demo-secret"):
    head = b64(json.dumps(header, separators=(",", ":")).encode())
    body = b64(json.dumps(payload, separators=(",", ":")).encode())
    signature = b64(hmac.new(secret.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest())
    return f"{head}.{body}.{signature}"


PAYLOAD = {"sub": "123", "iss": "https://auth.example.com", "aud": "app", "iat": 1000,
           "nbf": 1000, "exp": 5000}
TOKEN = make({"alg": "HS256", "typ": "JWT"}, PAYLOAD)


def test_decode_reads_header_payload_and_signature():
    parsed = jd.decode(TOKEN)
    assert parsed["header"] == {"alg": "HS256", "typ": "JWT"} and parsed["payload"] == PAYLOAD
    assert len(parsed["signature"]) == 32 and parsed["signing_input"].count(b".") == 1


def test_whitespace_and_bearer_prefix_are_ignored():
    head, body, sig = TOKEN.split(".")
    assert jd.decode(f"Bearer {head}.\n{body}.{sig}  ")["payload"] == PAYLOAD
    assert jd.decode(f"bearer {TOKEN}")["header"]["alg"] == "HS256"


def test_unsigned_token_has_an_empty_signature():
    head = b64(b'{"alg":"none"}')
    body = b64(b'{"sub":"x"}')
    parsed = jd.decode(f"{head}.{body}.")
    assert parsed["signature"] == b""


@pytest.mark.parametrize("token,message", [
    ("only.two", "3 dot-separated parts, this has 2"), ("a.b.c.d", "this has 4"),
    ("!!!.e30.sig", "header isn't valid base64url JSON"),
    (f"{b64(b'[1]')}.e30.x", "header should be a JSON object"),
    (f"{b64(b'{}')}.{b64(b'not json')}.x", "payload isn't valid base64url JSON")])
def test_bad_tokens(token, message):
    with pytest.raises(ValueError, match=message):
        jd.decode(token)


def test_timeline_and_status():
    rows = jd.timeline(PAYLOAD, now=3000)
    assert [(r[0], r[2], r[3]) for r in rows] == [
        ("iat", "1970-01-01 00:16:40 UTC", "33m 20s ago"),
        ("nbf", "1970-01-01 00:16:40 UTC", "33m 20s ago"),
        ("exp", "1970-01-01 01:23:20 UTC", "in 33m 20s")]
    assert jd.status(PAYLOAD, 3000) == "within its validity window"
    assert jd.status(PAYLOAD, 5000) == "EXPIRED" and jd.status(PAYLOAD, 999) == "NOT YET VALID"
    assert jd.status({"sub": "x"}, 1) == "no expiry claim"
    assert jd.timeline({"exp": "soon"}, 0)[0][3] == "not a valid timestamp"


@pytest.mark.parametrize("seconds,text", [(59, "0m 59s"), (3700, "1h 1m"), (90000, "1d 1h")])
def test_span_text(seconds, text):
    assert jd.span_text(seconds) == text


def test_warnings():
    assert jd.warnings({"alg": "none"}, PAYLOAD, 3000)[0].startswith("alg is 'none'")
    assert any("shared secret" in w for w in jd.warnings({"alg": "HS256"}, PAYLOAD, 3000))
    assert any("no exp claim" in w for w in jd.warnings({"alg": "RS256"}, {"iss": "x"}, 0))
    assert any("names its own key (jku)" in w
               for w in jd.warnings({"alg": "RS256", "jku": "https://evil.example"}, PAYLOAD, 0))
    far = {**PAYLOAD, "exp": 3000 + 400 * 86400}
    assert any("more than a year" in w for w in jd.warnings({"alg": "RS256"}, far, 3000))
    assert any("no iss or aud" in w for w in jd.warnings({"alg": "RS256"}, {"exp": 9}, 0))
    assert jd.warnings({"alg": "RS256"}, PAYLOAD, 3000) == []


def test_signature_check():
    parsed = jd.decode(TOKEN)
    assert jd.check_signature(parsed, parsed["header"], "demo-secret") is True
    assert jd.check_signature(parsed, parsed["header"], "other") is False
    assert jd.check_signature(parsed, {"alg": "RS256"}, "demo-secret") is None


def test_moment_parsing():
    assert jd.moment_to_seconds("1700000000") == 1700000000
    assert jd.moment_to_seconds("2023-11-14T22:13:20") == 1700000000
    assert jd.moment_to_seconds("2023-11-14T23:13:20+01:00") == 1700000000


def test_cli_text(capsys):
    assert jd.main([TOKEN, "--now", "3000"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("NOT VERIFIED") and '"alg": "HS256"' in out
    assert "Status: within its validity window" in out and "exp  expires" in out
    assert "Signature part: 32 byte(s)" in out and "shared secret" in out
    assert jd.main([TOKEN, "--now", "9000"]) == 0
    assert "Status: EXPIRED" in capsys.readouterr().out


def test_cli_json_and_file(tmp_path, capsys):
    path = tmp_path / "t.txt"
    path.write_text(TOKEN + "\n")
    assert jd.main(["--file", str(path), "--format", "json", "--now", "3000"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["payload"]["sub"] == "123" and data["verified"] is None
    assert data["status"] == "within its validity window" and data["signature_bytes"] == 32


def test_cli_secret_verification(monkeypatch, capsys):
    monkeypatch.setenv("JWT_TEST_SECRET", "demo-secret")
    assert jd.main([TOKEN, "--secret-env", "JWT_TEST_SECRET", "--now", "3000"]) == 0
    assert "Signature: valid for the secret you provided" in capsys.readouterr().out
    monkeypatch.setenv("JWT_TEST_SECRET", "wrong")
    assert jd.main([TOKEN, "--secret-env", "JWT_TEST_SECRET", "--now", "3000"]) == 1
    assert "INVALID" in capsys.readouterr().out
    other = make({"alg": "RS256"}, PAYLOAD)
    assert jd.main([other, "--secret-env", "JWT_TEST_SECRET", "--now", "3000"]) == 0
    assert "can't be checked here (algorithm RS256)" in capsys.readouterr().out
    monkeypatch.delenv("JWT_TEST_SECRET")
    assert jd.main([TOKEN, "--secret-env", "JWT_TEST_SECRET"]) == 1
    assert "is not set" in capsys.readouterr().err


def test_cli_errors(tmp_path, capsys):
    assert jd.main(["not-a-token"]) == 1
    assert "Can't decode that token" in capsys.readouterr().err
    assert jd.main(["--file", str(tmp_path / "none.txt")]) == 1
    assert jd.main([TOKEN, "--now", "yesterday"]) == 1
