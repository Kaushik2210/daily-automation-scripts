import json

import dns_lookup as dl
import pytest


def answer(rtype, *data, ttl=300):
    return {"Status": 0, "Answer": [{"name": "example.com.", "type": rtype, "TTL": ttl, "data": d}
                                    for d in data]}


def test_explain_txt_recognises_common_kinds():
    assert "SPF" in dl.explain_txt("v=spf1 include:x ~all")
    assert "DMARC" in dl.explain_txt("V=DMARC1; p=reject")
    assert "Google" in dl.explain_txt("google-site-verification=abc")
    assert dl.explain_txt("random text") == ""


def test_format_record_by_type():
    assert dl.format_record("MX", "10 mail.example.com.") == "priority 10  mail.example.com"
    assert dl.format_record("NS", "a.iana-servers.net.") == "a.iana-servers.net"
    assert dl.format_record("A", "1.2.3.4") == "1.2.3.4"
    long_txt = '"v=spf1 include:a.example " "include:b.example ~all"'  # split into 2 strings
    assert dl.format_record("TXT", long_txt).startswith(
        "v=spf1 include:a.example include:b.example ~all   [SPF")


def test_render_answers_and_empty_results():
    assert dl.render("example.com", "A", answer(1, "1.1.1.1", "2.2.2.2")) == [
        "A      1.1.1.1  (TTL 300s)", "       2.2.2.2  (TTL 300s)"]
    assert dl.render("example.com", "MX", {"Status": 0}) == ["MX     no MX records"]
    alias = {"Status": 0, "Answer": [{"type": 5, "TTL": 60, "data": "real.example.net."}]}
    assert dl.render("www.example.com", "A", alias) == [
        "A      no A records (it's an alias for real.example.net)"]


def test_render_dns_errors():
    assert "does not exist" in dl.render("x.example", "A", {"Status": 3})[0]
    assert "server failed" in dl.render("x.example", "A", {"Status": 2})[0]
    assert "DNS error 9" in dl.render("x.example", "A", {"Status": 9})[0]


def test_cli_from_saved_answers(tmp_path, capsys):
    saved = tmp_path / "dns.json"
    saved.write_text(json.dumps({"A": answer(1, "93.184.216.34"),
                                 "MX": answer(15, "10 mail.example.com.", "20 mail2.example.com."),
                                 "TXT": answer(16, '"v=spf1 -all"')}))
    assert dl.main(["Example.COM.", "--types", "a,mx,txt", "--from-file", str(saved)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("DNS records for example.com")
    assert "A      93.184.216.34" in out and "priority 20  mail2.example.com" in out
    assert "[SPF: which servers may send mail" in out


def test_nxdomain_makes_the_exit_code_1(tmp_path, capsys):
    saved = tmp_path / "dns.json"
    saved.write_text(json.dumps({"A": {"Status": 3}}))
    assert dl.main(["nope.example.com", "--types", "A", "--from-file", str(saved)]) == 1


def test_live_lookups_go_through_query(monkeypatch, capsys):
    asked = []

    def fake_query(domain, record_type, resolver, timeout):
        asked.append((domain, record_type, resolver))
        if record_type == "MX":
            raise OSError("no network")
        return answer(1, "9.9.9.9")

    monkeypatch.setattr(dl, "query", fake_query)
    assert dl.main(["example.com", "--types", "A,MX", "--resolver", "google"]) == 1
    assert asked == [("example.com", "A", "google"), ("example.com", "MX", "google")]
    assert "MX     lookup failed (no network)" in capsys.readouterr().out


def test_bad_arguments(tmp_path, capsys):
    for args in (["not a domain"], ["localhost"], ["example.com", "--types", "A,BOGUS"],
                 ["example.com", "--types", ","]):
        with pytest.raises(SystemExit):
            dl.main(args)
    assert dl.main(["example.com", "--from-file", str(tmp_path / "gone.json")]) == 1
    bad = tmp_path / "bad.json"
    bad.write_text("{oops")
    assert dl.main(["example.com", "--from-file", str(bad)]) == 1
