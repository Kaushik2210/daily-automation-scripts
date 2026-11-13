from datetime import UTC, date, datetime

import pytest
import ssl_expiry_checker as sec

# A self-signed demo certificate made only for these tests (valid 2026-01-01 to 2026-04-01 12:00).
PEM = """-----BEGIN CERTIFICATE-----
MIIB7TCCAZKgAwIBAgIUJxRQwl6B3gF4vFTH8yN0fWcLhWcwCgYIKoZIzj0EAwIw
NzELMAkGA1UEBhMCVVMxETAPBgNVBAoMCFRlc3QgT3JnMRUwEwYDVQQDDAx0ZXN0
LmV4YW1wbGUwHhcNMjYwMTAxMDAwMDAwWhcNMjYwNDAxMTIwMDAwWjA3MQswCQYD
VQQGEwJVUzERMA8GA1UECgwIVGVzdCBPcmcxFTATBgNVBAMMDHRlc3QuZXhhbXBs
ZTBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABG0vExJGjL0Rwgwi7XAAYSe5P7co
jIfDOhe+vGX5p4Bm+vbAjjxti1ZPhFhiQMCsJ2TaSd+v06XYt1RpAaWSIIGjfDB6
MB0GA1UdDgQWBBRWXVbi5cUaDN7UNsN+WPyp5hLCeTAfBgNVHSMEGDAWgBRWXVbi
5cUaDN7UNsN+WPyp5hLCeTAnBgNVHREEIDAeggx0ZXN0LmV4YW1wbGWCDioud2ls
ZC5leGFtcGxlMA8GA1UdEwEB/wQFMAMBAf8wCgYIKoZIzj0EAwIDSQAwRgIhAPl0
1E/ejkjWKA1A1T76Rt1ETYWhxV0/Kv60c8lXN88VAiEAiCBDow1q3COiYCXaCIWu
2bvxxWOq9ghOozg2SZ/JKew=
-----END CERTIFICATE-----
"""


def test_decode_oid_and_lengths():
    assert sec.decode_oid(bytes([0x55, 0x04, 0x03])) == "2.5.4.3"
    assert sec.decode_oid(bytes([0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D, 0x01, 0x01, 0x0B])) == (
        "1.2.840.113549.1.1.11")
    tag, value, end = sec.read_tlv(bytes([0x04, 0x82, 0x01, 0x00]) + b"x" * 256)
    assert (tag, len(value), end) == (0x04, 256, 260)


def test_parse_a_real_certificate():
    der = sec.pem_to_der(PEM)[0]
    cert = sec.parse_certificate(der)
    assert cert["subject"] == [("C", "US"), ("O", "Test Org"), ("CN", "test.example")]
    assert cert["issuer"] == cert["subject"]
    assert cert["san"] == ["test.example", "*.wild.example"]
    assert cert["is_ca"] is True and cert["serial"].startswith("271450c25e81")
    assert cert["not_before"] == datetime(2026, 1, 1, tzinfo=UTC)
    assert cert["not_after"] == datetime(2026, 4, 1, 12, 0, tzinfo=UTC)


def test_pem_to_der_finds_every_certificate_in_a_bundle():
    assert len(sec.pem_to_der(PEM + PEM)) == 2 and sec.pem_to_der("no certificate here") == []


def test_decode_time_handles_both_formats():
    assert sec.decode_time(0x17, b"261231235959Z") == datetime(2026, 12, 31, 23, 59, 59, tzinfo=UTC)
    assert sec.decode_time(0x17, b"991231235959Z").year == 1999
    assert sec.decode_time(0x18, b"20501231000000Z").year == 2050


@pytest.mark.parametrize("host,names,expected", [
    ("example.com", ["example.com"], True), ("EXAMPLE.com", ["example.COM"], True),
    ("www.example.com", ["*.example.com"], True), ("a.b.example.com", ["*.example.com"], False),
    ("example.com", ["*.example.com"], False), ("evil.com", ["example.com"], False)])
def test_host_matches(host, names, expected):
    assert sec.host_matches(host, names) is expected


def test_judge_statuses():
    cert = sec.parse_certificate(sec.pem_to_der(PEM)[0])
    assert sec.judge(cert, "", date(2026, 3, 1), 30) == ("OK", 31)
    assert sec.judge(cert, "", date(2026, 3, 10), 30) == ("EXPIRING SOON", 22)
    assert sec.judge(cert, "", date(2026, 4, 2), 30) == ("EXPIRED", -1)
    assert sec.judge(cert, "test.example", date(2026, 3, 1), 30)[0] == "OK"
    assert sec.judge(cert, "other.example", date(2026, 3, 1), 30)[0] == "NAME MISMATCH"
    assert sec.judge(cert, "a.wild.example", date(2026, 3, 1), 30)[0] == "OK"


def test_cli_reads_pem_files(tmp_path, capsys):
    path = tmp_path / "site.pem"
    path.write_text(PEM)
    assert sec.main([str(path), "--today", "2026-03-01"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("OK") and "expires 2026-04-01 (31 day(s) left)" in out
    assert "subject test.example; issuer test.example" in out
    assert "names   test.example, *.wild.example" in out
    assert sec.main([str(path), "--today", "2026-03-20"]) == 1
    assert "EXPIRING SOON" in capsys.readouterr().out
    assert sec.main([str(path), "--today", "2026-05-01", "--warn-days", "0"]) == 1
    out = capsys.readouterr().out
    assert out.startswith("EXPIRED") and "(30 day(s) ago)" in out


def test_cli_live_domains_use_the_fetcher(monkeypatch, capsys):
    calls = []

    def fake_fetch(host, port, timeout):
        calls.append((host, port))
        if host == "broken.example":
            raise OSError("connection refused")
        return sec.pem_to_der(PEM)[0]

    monkeypatch.setattr(sec, "fetch_certificate", fake_fetch)
    targets = ["test.example", "broken.example:8443", "other.example"]
    code = sec.main([*targets, "--today", "2026-03-01"])
    out = capsys.readouterr().out
    assert code == 1 and calls == [("test.example", 443), ("broken.example", 8443),
                                   ("other.example", 443)]
    assert "OK" in out and "test.example:443" in out
    assert "?  broken.example:8443: couldn't check (connection refused)" in out
    assert "NAME MISMATCH" in out


def test_bad_inputs(tmp_path, capsys):
    junk = tmp_path / "junk.pem"
    junk.write_text("not a certificate")
    assert sec.main([str(junk)]) == 1
    assert "couldn't check" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        sec.main([str(junk), "--today", "soon"])
