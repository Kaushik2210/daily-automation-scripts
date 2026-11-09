import email
import email.policy

import header_analyzer as ha

RAW = """Return-Path: <bounce@mailer.brief.example>
Received: from mx1.example.org (mx1.example.org [203.0.113.10]) by inbox.example.org with ESMTPS
 id a; Mon, 02 Nov 2026 07:30:09 +0000
Received: from relay.brief.example (relay.brief.example [198.51.100.7]) by mx1.example.org
 with ESMTP id b; Mon, 02 Nov 2026 07:30:05 +0000
Received: from app01.brief.example (localhost [127.0.0.1]) by relay.brief.example with ESMTP
 id c; Mon, 02 Nov 2026 07:29:02 +0000
Authentication-Results: inbox.example.org; spf=pass smtp.mailfrom=x; dkim=pass header.d=y;
 dmarc=fail header.from=brief.example
DKIM-Signature: v=1; a=rsa-sha256; d=brief.example; s=k; b=abc
From: Daily Brief <news@brief.example>
To: Sam <sam@example.org>
Subject: Hello
Date: Mon, 02 Nov 2026 07:29:00 +0000

body
"""


def parse(text):
    return email.message_from_string(text, policy=email.policy.default)


def test_parse_received_extracts_hosts_and_time():
    hop = ha.parse_received("from a.test (a.test [1.2.3.4])\n by b.test with SMTP id x;"
                            " Mon, 02 Nov 2026 07:30:05 +0100")
    assert (hop["from"], hop["by"], hop["detail"]) == ("a.test", "b.test", "a.test [1.2.3.4]")
    assert hop["when"].isoformat() == "2026-11-02T07:30:05+01:00"
    odd = ha.parse_received("by only.test; not a date")
    assert (odd["from"], odd["by"], odd["when"]) == ("?", "only.test", None)


def test_hops_are_oldest_first():
    hops = ha.build_hops(parse(RAW))
    assert [h["by"] for h in hops] == ["relay.brief.example", "mx1.example.org",
                                       "inbox.example.org"]


def test_auth_results_from_header_and_received_spf_fallback():
    assert ha.auth_results(parse(RAW)) == {"spf": "pass", "dkim": "pass", "dmarc": "fail"}
    fallback = parse("Received-SPF: Fail (domain does not designate)\n\nx")
    assert ha.auth_results(fallback) == {"spf": "fail"}
    assert ha.auth_results(parse("Subject: x\n\ny")) == {}


def test_warnings_cover_auth_alignment_reply_to_and_slow_hops():
    msg = parse(RAW)
    warnings = ha.find_warnings(msg, ha.build_hops(msg), ha.auth_results(msg))
    assert warnings == ["DMARC result is 'fail'"]  # a sub-domain Return-Path is aligned
    odd = parse(RAW.replace("bounce@mailer.brief.example", "x@evil.test")
                .replace("Subject: Hello", "Reply-To: boss@other.test\nSubject: Hello")
                .replace("07:30:05", "07:45:05"))
    found = ha.find_warnings(odd, ha.build_hops(odd), ha.auth_results(odd))
    assert any("Return-Path domain (evil.test)" in w for w in found)
    assert any("Reply-To goes to a different domain (other.test)" in w for w in found)
    assert any("hop 2 took 16 minutes" in w for w in found)


def test_missing_auth_results_are_flagged():
    msg = parse("From: a@x.test\n\nbody")
    assert "no SPF/DKIM/DMARC results" in ha.find_warnings(msg, [], {})[0]


def test_cli_report(tmp_path, capsys):
    path = tmp_path / "m.eml"
    path.write_text(RAW)
    assert ha.main([str(path)]) == 1  # the DMARC failure
    out = capsys.readouterr().out
    assert "Route (3 hop(s), oldest first):" in out
    assert "1. app01.brief.example -> relay.brief.example" in out and "(+" in out
    assert "total transit: 67 seconds" in out
    assert "DMARC fail" in out and "signed by brief.example" in out
    assert "! DMARC result is 'fail'" in out


def test_clean_message_has_no_warnings_and_missing_file(tmp_path, capsys):
    path = tmp_path / "ok.eml"
    path.write_text(RAW.replace("dmarc=fail", "dmarc=pass"))
    assert ha.main([str(path)]) == 0
    assert "No warnings." in capsys.readouterr().out
    assert ha.main([str(tmp_path / "gone.eml")]) == 1
