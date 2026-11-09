import email_validator as ev
import pytest


@pytest.mark.parametrize("address", [
    "alice@acme.test", "bob.smith+news@example.com", "name@sub-domain.example.co.uk",
    "o'brien@example.org", "x@münchen.example", "a@b.io", "user_1@xn--mnchen-3ya.de"])
def test_valid_addresses(address):
    assert ev.check_syntax(address) is None


@pytest.mark.parametrize("address,reason", [
    ("not-an-email", "missing @"), ("sam@@example.org", "exactly one @"),
    ("@example.com", "nothing before"), (".dot@example.com", "dots in the wrong"),
    ("trailing.@example.com", "dots in the wrong"), ("a..b@example.com", "dots in the wrong"),
    ("user@-bad-.com", "hyphens"), ("user@localhost", "needs a dot"),
    ("user@example.", "needs a dot"), ("ünïcode@example.com", "non-ASCII"),
    ("sp ace@example.com", "unusual characters"), ("a@b.123", "can't end in a number"),
    ("x" * 65 + "@example.com", "longer than 64"),
    ("a@" + "b" * 64 + ".com", "too long"),
    ("a@" + ("b" * 60 + ".") * 5 + "com", "longer than 254")])
def test_invalid_addresses(address, reason):
    assert reason in ev.check_syntax(address)


def fake_dns(answers):
    def query(domain, record_type, timeout=10):
        return {"Answer": answers.get((domain, record_type), [])}
    return query


def test_lookup_mx_orders_by_priority_and_falls_back_to_a(monkeypatch):
    monkeypatch.setattr(ev, "dns_query", fake_dns({
        ("a.test", "MX"): [{"type": 15, "data": "20 backup.a.test."},
                           {"type": 15, "data": "10 mx.a.test."}],
        ("b.test", "A"): [{"type": 1, "data": "192.0.2.1"}]}))
    assert ev.lookup_mx("a.test") == ("mx", ["mx.a.test", "backup.a.test"])
    assert ev.lookup_mx("b.test") == ("a", [])
    assert ev.lookup_mx("c.test") == ("none", [])


def test_null_mx_counts_as_no_mail(monkeypatch):
    monkeypatch.setattr(ev, "dns_query", fake_dns({("n.test", "MX"): [
        {"type": 15, "data": "0 ."}]}))
    assert ev.lookup_mx("n.test") == ("none", [])


def test_read_list_skips_comments(tmp_path):
    f = tmp_path / "e.txt"
    f.write_text("# header\na@b.co\n\n  c@d.co \n")
    assert ev.read_list(f) == ["a@b.co", "c@d.co"]


def test_cli_no_mx_makes_no_requests(monkeypatch, capsys):
    def boom(*args, **kwargs):
        raise AssertionError("network used")
    monkeypatch.setattr(ev, "dns_query", boom)
    assert ev.main(["good@example.com", "bad@@x", "--no-mx"]) == 1
    out = capsys.readouterr().out
    assert "ok    good@example.com  (syntax only)" in out and "BAD   bad@@x" in out
    assert "1 of 2 address(es) look fine." in out


def test_cli_with_mx_results_and_caching(monkeypatch, capsys):
    calls = []

    def lookup(domain):
        calls.append(domain)
        return {"good.test": ("mx", ["mail.good.test"]), "old.test": ("a", [])}.get(
            domain, ("none", []))

    monkeypatch.setattr(ev, "lookup_mx", lookup)
    args = ["a@good.test", "b@good.test", "c@old.test", "d@dead.test"]
    assert ev.main(args) == 1
    out = capsys.readouterr().out
    assert "(mail server: mail.good.test)" in out and "warn  c@old.test" in out
    assert "BAD   d@dead.test  (domain has no mail server)" in out
    assert calls == ["good.test", "old.test", "dead.test"]


def test_lookup_failures_are_reported(monkeypatch, capsys):
    def offline(domain):
        raise OSError("no network")

    monkeypatch.setattr(ev, "lookup_mx", offline)
    assert ev.main(["a@good.test"]) == 1
    assert "??    a@good.test" in capsys.readouterr().out


def test_file_input_and_errors(tmp_path, capsys):
    f = tmp_path / "e.txt"
    f.write_text("a@b.co\n")
    assert ev.main(["--file", str(f), "--no-mx"]) == 0
    assert ev.main(["--file", str(tmp_path / "gone.txt"), "--no-mx"]) == 1
    with pytest.raises(SystemExit):
        ev.main([])
