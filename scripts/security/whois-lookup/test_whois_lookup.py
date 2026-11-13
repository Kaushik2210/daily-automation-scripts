import socket
import threading
from datetime import date

import pytest
import whois_lookup as wl

SAMPLE = """Domain Name: EXAMPLE.COM
Registrar WHOIS Server: whois.registrar.example
Updated Date: 2026-08-14T07:01:31Z
Creation Date: 1995-08-14T04:00:00Z
Registry Expiry Date: 2027-08-13T04:00:00Z
Registrar: Example Registrar, Inc.
Registrar Abuse Contact Email: abuse@registrar.example
Domain Status: clientDeleteProhibited https://icann.org/epp#clientDeleteProhibited
Domain Status: clientTransferProhibited https://icann.org/epp#clientTransferProhibited
Registrant Organization: Internet Assigned Numbers Authority
Registrant Country: US
Name Server: A.IANA-SERVERS.NET
Name Server: B.IANA-SERVERS.NET
Name Server: A.IANA-SERVERS.NET
DNSSEC: signedDelegation
>>> Last update of WHOIS database: 2026-11-13T00:00:00Z <<<
"""


def test_parse_whois_fields_lists_and_dedupe():
    info = wl.parse_whois(SAMPLE)
    assert info["domain"] == "EXAMPLE.COM" and info["registrar"] == "Example Registrar, Inc."
    assert info["expires"] == "2027-08-13T04:00:00Z" and info["dnssec"] == "signedDelegation"
    assert info["status"] == ["clientDeleteProhibited", "clientTransferProhibited"]
    assert info["name servers"] == ["a.iana-servers.net", "b.iana-servers.net"]
    assert info["organisation"].startswith("Internet Assigned") and info["country"] == "US"
    assert "Last update" not in str(info)


def test_parse_other_registry_styles():
    nominet = "domain: example.uk\nnserver: ns1.example.uk\nnserver: ns2.example.uk\n"
    info = wl.parse_whois(nominet)
    assert info["domain"] == "example.uk" and info["name servers"] == ["ns1.example.uk",
                                                                       "ns2.example.uk"]
    assert wl.parse_whois("% comment only\n# another\n\nno colon line") == {}


@pytest.mark.parametrize("text,expected", [
    ("2027-08-13T04:00:00Z", date(2027, 8, 13)), ("2027-08-13", date(2027, 8, 13)),
    ("13-aug-2027", date(2027, 8, 13)), ("2027.08.13", date(2027, 8, 13)),
    ("2027-08-13 04:00:00 (UTC)", date(2027, 8, 13)), ("2027-08-13T04:00:00+0100",
                                                       date(2027, 8, 13)),
    ("someday", None)])
def test_parse_date(text, expected):
    assert wl.parse_date(text) == expected


def test_describe_expiry():
    today = date(2026, 11, 13)
    assert wl.describe_expiry("2027-08-13T04:00:00Z", today) == "2027-08-13 (273 day(s) left)"
    assert wl.describe_expiry("2026-11-01", today) == "2026-11-01 (expired 12 day(s) ago)"
    assert wl.describe_expiry("unparseable", today) == "unparseable"


def test_render_lines_and_empty_result():
    lines = wl.render(wl.parse_whois(SAMPLE), date(2026, 11, 13))
    def row(label, value=""):
        return f"{label:<15}{value}"

    assert lines[0] == row("Domain:", "EXAMPLE.COM")
    assert row("Created:", "1995-08-14") in lines
    assert row("Expires:", "2027-08-13 (273 day(s) left)") in lines
    assert lines.count(row("", "b.iana-servers.net")) == 1
    assert row("Status:", "clientDeleteProhibited") in lines
    assert "No registration details" in wl.render({}, date(2026, 11, 13))[0]


def test_cli_from_file_and_raw(tmp_path, capsys):
    path = tmp_path / "whois.txt"
    path.write_text(SAMPLE)
    assert wl.main(["--from-file", str(path), "--today", "2026-11-13"]) == 0
    out = capsys.readouterr().out
    assert f"{'Registrar:':<15}Example Registrar, Inc." in out and "raw WHOIS" not in out
    assert wl.main(["--from-file", str(path), "--raw"]) == 0
    assert "----- raw WHOIS text -----" in capsys.readouterr().out
    path.write_text("nothing useful")
    assert wl.main(["--from-file", str(path)]) == 1


class FakeWhois:
    """A tiny WHOIS server on localhost that answers IANA-style and registry-style queries."""

    def __init__(self, answers):
        self.answers, self.queries = answers, []
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(5)
        self.port = self.sock.getsockname()[1]
        threading.Thread(target=self.serve, daemon=True).start()

    def serve(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            query = conn.recv(256).decode().strip()
            self.queries.append(query)
            conn.sendall(self.answers.get(query, "").encode())
            conn.close()


@pytest.fixture
def whois_server(monkeypatch):
    server = FakeWhois({
        "com": "refer:        127.0.0.1\n",
        "example.com": SAMPLE.replace("whois.registrar.example", "localhost")})
    monkeypatch.setattr(wl, "IANA", "127.0.0.1")
    monkeypatch.setattr(wl, "PORT", server.port)
    yield server
    server.sock.close()


def test_live_lookup_asks_iana_then_the_registry(whois_server, capsys):
    assert wl.main(["Example.com.", "--today", "2026-11-13"]) == 0
    assert whois_server.queries[:2] == ["com", "example.com"]
    assert f"{'Registrar:':<15}Example Registrar, Inc." in capsys.readouterr().out


def test_lookup_follows_the_registrar_server_unless_told_not_to(whois_server):
    wl.lookup("example.com", timeout=2)
    assert whois_server.queries == ["com", "example.com", "example.com"]
    whois_server.queries.clear()
    wl.lookup("example.com", timeout=2, follow=False)
    assert whois_server.queries == ["com", "example.com"]


def test_unknown_tld_and_bad_arguments(whois_server, capsys):
    assert wl.main(["example.zz"]) == 1
    assert "couldn't find a WHOIS server" in capsys.readouterr().err
    for args in ([], ["not a domain"], ["localhost"], ["example.com", "--today", "soon"]):
        with pytest.raises(SystemExit):
            wl.main(args)
