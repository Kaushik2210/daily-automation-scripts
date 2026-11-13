import cert_chain_viewer as ccv
import pytest

CHAIN = """-----BEGIN CERTIFICATE-----
MIIEATCCAmmgAwIBAgIUYpnt+qNuy80K6wS64iL/miCH1lswDQYJKoZIhvcNAQEL
BQAwQzELMAkGA1UEBhMCVVMxEzARBgNVBAoMCkRlbW8gVHJ1c3QxHzAdBgNVBAMM
FkRlbW8gSW50ZXJtZWRpYXRlIENBIDEwHhcNMjYxMDAxMDAwMDAwWhcNMjcwMTAx
MDAwMDAwWjAWMRQwEgYDVQQDDAtleGFtcGxlLmNvbTCCASIwDQYJKoZIhvcNAQEB
BQADggEPADCCAQoCggEBAJyKYLfEauCvCtCUV879aNvsqxOUrgguXRmXixcJU65U
mhwQgW8Dm2YICsSOsp+mCwBnMKBTsGexz40nmicDSO/08FXA2xkE/i5a5yokoc3u
U+syM9wVmABNZdLvA19cBmgSukUHnQteY0WZNTGeBldnhBlRXDFmgHWubmRVaFtZ
h2G/H0TZaPVZjsYh/Zr0LxGzGm2ztLvBvvI54HY+06tQ57uN8sESkqHIg+9R98qZ
/19zf/7CqZbB3FuuBhXzufcbey+IQ3H3jJkGD9X7gJAqX61U1m/0pESOo4vp4oH0
Ndv+fDcSJ2V5TlZqJzLSEpb8BqoGhJq5J1yFWCvIVPkCAwEAAaOBmTCBljAJBgNV
HRMEAjAAMAsGA1UdDwQEAwIFoDATBgNVHSUEDDAKBggrBgEFBQcDATAnBgNVHREE
IDAeggtleGFtcGxlLmNvbYIPd3d3LmV4YW1wbGUuY29tMB0GA1UdDgQWBBR6dnRY
i4Niux8Mtj36/gUQjYi5+zAfBgNVHSMEGDAWgBRiCm+aAzSU9pXhVeVr5zwl4QfS
TzANBgkqhkiG9w0BAQsFAAOCAYEAYgHexZkjsAQ68EhWb6xWr2XgQZS3ebFcptFg
WB8JyRoOOahv9hvYwjowIP62jTqTqKLk53b73BH79frs2Pxpcx9lVsGs6jtaVtJ5
OeUtfcqfs+4Ngd/ydhWD43qcLV8iUjxdZywL6yup0740pfpv37pDFDOOsK0Kkwym
iwoSx4NBfW9/lT1qtmRf9uR5vvfiWPc1TFFT97Qn8Vwj5ax2wa5yKHR5B7z0hSdN
BBUp+SGjgaxy2cz7iBvHDAYtzpkAuTAuVey3jHxqqB3nfl5MYl9PB3S3e+NevyHa
n7vrYjVNqxqWQjJXNcpEwAGlmM259a8+IIL65vAk5Ul8iiEiN4uKNu+P5dpHvsic
SmoXzIlNr4H3DEahsrPJt3FovN52k60uZQo3mHSOAZ07PfBOeWrTtHZgi4vixxr1
WG3N9r8WvQDBMz5ZpShjEFxjA6kr/bMy5bsKQNE07K3krkSxKgAB5EaNPVGD/e8f
keV2MsETqn78qTgvr1kZXtnLTDan
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIDTjCCAtWgAwIBAgIUEzYk/ncCAutTzKloQ4V4zJwTtpQwCgYIKoZIzj0EAwIw
OTELMAkGA1UEBhMCVVMxEzARBgNVBAoMCkRlbW8gVHJ1c3QxFTATBgNVBAMMDERl
bW8gUm9vdCBDQTAeFw0yNDAxMDEwMDAwMDBaFw0zMDAxMDEwMDAwMDBaMEMxCzAJ
BgNVBAYTAlVTMRMwEQYDVQQKDApEZW1vIFRydXN0MR8wHQYDVQQDDBZEZW1vIElu
dGVybWVkaWF0ZSBDQSAxMIIBojANBgkqhkiG9w0BAQEFAAOCAY8AMIIBigKCAYEA
0MCUc/OD9vGqd45Tibg/9aJPyC1nsoPkBqi6AbJvQ5emh877y+v8HB8fhAz/zR//
4srm3dDgDriAC8FbnIGfBAdDqkMdqO0z3h7L+cZg/a2FYEuJxFv3Ene+FKWBiuQT
W4TTpPyRnoe34EgPNwSgs37evKjj9tJ3xditqexSz2BndI25FKZN6OoWhhShqI7V
Af2K5siDZPPYDX2vWJ9brlFchXXb5hk0Ond3IZj3gIi7ripJHH+cQTT+GomiREBV
oe1FK68LJPeyIvi0d2vJgaWw77pMlA+ONAt/Z1Vs9RVbYfi7JHKo89+WBB9zwXd3
bF+8aQPIv9oSP1thFHhRneNgHyhcRvwin2Hk90ui8f+Lrg3Azcjvoz/OUZWazaA4
PvWEBtXnUCRNzXNcb37GmQGivaSx0qm73psXFho+RoaSJ1lLfEiMBkJSWtyMtupv
apURMQEkXtlOQZwVEm/gO3agln6QPnSO/5USi0rZiej1HPRJa1D6Ray0TWoJPKQZ
AgMBAAGjZjBkMBIGA1UdEwEB/wQIMAYBAf8CAQAwDgYDVR0PAQH/BAQDAgEGMB0G
A1UdDgQWBBRiCm+aAzSU9pXhVeVr5zwl4QfSTzAfBgNVHSMEGDAWgBQThJpGd8SH
5Ucgqh/xmTgcZrHqPjAKBggqhkjOPQQDAgNnADBkAjBdVseQNx1QrZoVJll5FBZI
pAqBTHYy0YzDZhFRVOanaeJJYP9ZCceZhYonm9lJLqQCMA0kr5rjfN2uZ0b78O/c
/IXtPF16x2pTBO+PMXGrQJWQN62HO7lz2bkRWxVzN5RsLg==
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIICEzCCAZqgAwIBAgIUOvxcSRXsBTcumn+GIkdYjVKEIn8wCgYIKoZIzj0EAwIw
OTELMAkGA1UEBhMCVVMxEzARBgNVBAoMCkRlbW8gVHJ1c3QxFTATBgNVBAMMDERl
bW8gUm9vdCBDQTAeFw0yNjExMTMwMjE5NTZaFw0zNjExMTAwMjE5NTZaMDkxCzAJ
BgNVBAYTAlVTMRMwEQYDVQQKDApEZW1vIFRydXN0MRUwEwYDVQQDDAxEZW1vIFJv
b3QgQ0EwdjAQBgcqhkjOPQIBBgUrgQQAIgNiAASGsz2gyyd7X5bsYT4gK30WpkHq
lYmD4+eZJbpWHySx9pumwo4+5aF51UiMtKsMj9gKtwmaYhLabmUY9U6EdxZyTOAQ
cKWiSs7vxS17gb6qGQrdQjR01SlvTddcIp0DXRujYzBhMB0GA1UdDgQWBBQThJpG
d8SH5Ucgqh/xmTgcZrHqPjAfBgNVHSMEGDAWgBQThJpGd8SH5Ucgqh/xmTgcZrHq
PjAPBgNVHRMBAf8EBTADAQH/MA4GA1UdDwEB/wQEAwIBBjAKBggqhkjOPQQDAgNn
ADBkAjAI0G5/yfdtDioxAMWLH/Hol02QaYYUf8EyM2WqPxS6tq403iMxLwNOpolg
MyXJa7ACMGa0JlfmxrBpqdzoMKkP4gcWjtnGPXwLBXphfmHLJNjjdpOSfHnYSZM6
As4L8KckAw==
-----END CERTIFICATE-----
"""
TODAY = "2026-11-13"


def split():
    return ccv.pem_to_der(CHAIN)


def test_parses_leaf_details():
    leaf = ccv.parse_certificate(split()[0])
    assert ccv.name_text(leaf["subject"]) == "example.com"
    assert ccv.name_text(leaf["issuer"]) == "Demo Intermediate CA 1"
    assert leaf["san"] == ["example.com", "www.example.com"]
    assert leaf["key"] == "RSA 2048-bit" and leaf["signature"] == "sha256WithRSA"
    assert leaf["not_after"].strftime("%Y-%m-%d") == "2027-01-01" and not leaf["is_ca"]


def test_parses_ca_flags_and_key_types():
    inter, root = (ccv.parse_certificate(d) for d in split()[1:])
    assert inter["is_ca"] and root["is_ca"]
    assert inter["key"] == "RSA 3072-bit" and root["key"] == "EC P-384"


def test_links_and_root_detection():
    certs = [ccv.parse_certificate(d) for d in split()]
    assert ccv.check_links(certs) == ["issued by the next certificate",
                                      "issued by the next certificate",
                                      "self-signed root (the end of the chain)"]
    partial = ccv.check_links(certs[:2])
    assert partial[-1].startswith("not self-signed")
    assert "DOES NOT MATCH" in ccv.check_links([certs[0], certs[0]])[0]


def test_fingerprint_format():
    fp = ccv.fingerprint(split()[0])
    assert len(fp.split(":")) == 32 and fp == fp.upper()


def test_cli_prints_chain_and_flags_expiry(tmp_path, capsys):
    path = tmp_path / "chain.pem"
    path.write_text(CHAIN)
    assert ccv.main([str(path), "--today", TODAY]) == 0
    out = capsys.readouterr().out
    assert out.startswith("3 certificate(s)") and "49 day(s) left" in out
    assert "(root CA)" in out and "(intermediate CA)" in out
    assert ccv.main([str(path), "--today", "2027-02-01"]) == 1
    assert "EXPIRED 31 day(s) ago" in capsys.readouterr().out


def test_empty_and_bad_input(tmp_path, capsys):
    empty = tmp_path / "empty.pem"
    empty.write_text("nothing here")
    assert ccv.main([str(empty)]) == 1
    assert "No certificates found" in capsys.readouterr().err
    assert ccv.main(["127.0.0.1:1", "--timeout", "1"]) == 1
    with pytest.raises(SystemExit):
        ccv.main([str(empty), "--today", "soon"])


def test_der_from_download():
    der = split()[0]
    assert ccv.der_from_download(der) == der
    assert ccv.der_from_download(CHAIN.encode()) == der
    assert ccv.der_from_download(b"<html>") is None


def test_fetch_chain_fails_cleanly_when_nothing_is_listening():
    with pytest.raises(OSError):
        ccv.fetch_chain("127.0.0.1", 1, timeout=1)
