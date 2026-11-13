import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import security_header_checker as shc

SECURE = """HTTP/2 200
strict-transport-security: max-age=63072000; includeSubDomains; preload
content-security-policy: default-src 'self'; frame-ancestors 'none'; object-src 'none'
x-content-type-options: nosniff
referrer-policy: strict-origin-when-cross-origin
permissions-policy: camera=(), microphone=()
cross-origin-opener-policy: same-origin
cross-origin-resource-policy: same-origin
set-cookie: session=abc; Path=/; Secure; HttpOnly; SameSite=Strict
"""
WEAK = """HTTP/1.1 200 OK
Server: nginx/1.24.0
X-Powered-By: Express
Strict-Transport-Security: max-age=3600
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'
Set-Cookie: a=1; Path=/
Set-Cookie: b=2; Secure; HttpOnly; SameSite=Lax
"""


def run(text):
    return shc.evaluate(shc.parse_headers(text))


def test_parse_headers_lowercases_keeps_repeats_and_uses_the_last_response():
    headers = shc.parse_headers("HTTP/1.1 301\nLocation: /x\n\nHTTP/2 200\nSet-Cookie: a=1\n"
                                "set-cookie: b=2\nServer: nginx\n")
    assert headers == {"set-cookie": ["a=1", "b=2"], "server": ["nginx"]}
    assert shc.parse_headers("") == {} and shc.parse_headers("garbage") == {}


def test_a_fully_hardened_response_scores_100():
    percent, grade, results = run(SECURE)
    assert (percent, grade) == (100, "A+")
    assert all(status == "PASS" for _, status, *_ in results)


def test_a_weak_response_gets_specific_findings():
    percent, grade, results = run(WEAK)
    by_name = {name: (status, message) for name, status, message, *_ in results}
    assert grade in ("D", "F") and percent < 40
    assert by_name["HSTS"][0] == "WARN" and "3600" in by_name["HSTS"][1]
    assert by_name["Content-Security-Policy"][0] == "WARN" and "unsafe-inline" in (
        by_name["Content-Security-Policy"][1])
    assert by_name["Cookies"][0] == "WARN" and "a lacks Secure/HttpOnly/SameSite" in (
        by_name["Cookies"][1])
    assert "nginx/1.24.0" in by_name["Info disclosure"][1]
    assert by_name["Clickjacking"][0] == "FAIL" and by_name["Permissions-Policy"][0] == "FAIL"


@pytest.mark.parametrize("percent,grade", [(100, "A+"), (95, "A+"), (94, "A"), (85, "A"),
                                           (70, "B"), (55, "C"), (40, "D"), (39, "F"), (0, "F")])
def test_grade_thresholds(percent, grade):
    assert shc.grade_for(percent) == grade


def test_individual_check_edge_cases():
    assert shc.check_hsts({})[2] == "FAIL"
    assert shc.check_hsts({"strict-transport-security": ["max-age=31536000"]})[:3] == (
        20, 20, "PASS")
    assert shc.check_csp({"content-security-policy": ["script-src *"]})[2] == "WARN"
    assert shc.check_csp({"content-security-policy": ["default-src 'self'"]})[2] == "PASS"
    assert shc.check_framing({"x-frame-options": ["sameorigin"]})[2] == "PASS"
    assert shc.check_referrer({"referrer-policy": ["unsafe-url"]})[2] == "WARN"
    assert shc.check_referrer({"referrer-policy": ["no-referrer, strict-origin"]})[2] == "PASS"
    assert shc.check_isolation({"cross-origin-opener-policy": ["same-origin"]})[2] == "WARN"
    assert shc.check_cookies({})[2] == "PASS"
    many = {"set-cookie": ["a=1", "b=2", "c=3", "d=4"]}
    assert shc.check_cookies(many)[:3] == (0, 10, "FAIL")
    assert shc.check_disclosure({"server": ["cloudflare"]})[2] == "PASS"


def test_cli_with_header_files(tmp_path, capsys):
    good, bad = tmp_path / "good.txt", tmp_path / "bad.txt"
    good.write_text(SECURE)
    bad.write_text(WEAK)
    assert shc.main([str(good)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("Security headers: grade A+ (100%)") and "[PASS] HSTS" in out
    assert shc.main([str(bad)]) == 1
    assert "[FAIL] Clickjacking" in capsys.readouterr().out
    assert shc.main([str(bad), "--min-grade", "F"]) == 0


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Strict-Transport-Security", "max-age=63072000")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Set-Cookie", "a=1; Secure; HttpOnly; SameSite=Lax")
        self.send_header("Set-Cookie", "b=2; Secure; HttpOnly; SameSite=Lax")
        self.end_headers()


def test_live_url_collects_repeated_headers(capsys):
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        headers = shc.fetch_headers(f"http://127.0.0.1:{server.server_address[1]}/")
        assert headers["set-cookie"] == ["a=1; Secure; HttpOnly; SameSite=Lax",
                                         "b=2; Secure; HttpOnly; SameSite=Lax"]
        assert shc.main([f"http://127.0.0.1:{server.server_address[1]}/", "--min-grade", "F"]) == 0
        assert "Cookies" in capsys.readouterr().out
    finally:
        server.shutdown()


def test_bad_input(tmp_path, capsys):
    empty = tmp_path / "empty.txt"
    empty.write_text("nothing")
    assert shc.main([str(empty)]) == 1
    assert shc.main(["http://127.0.0.1:9/"]) == 1
    with pytest.raises(SystemExit):
        shc.main([str(tmp_path / "gone.txt")])
