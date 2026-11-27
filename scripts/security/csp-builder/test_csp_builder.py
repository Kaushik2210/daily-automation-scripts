import json

import csp_builder as cb
import pytest


@pytest.mark.parametrize("source,ok", [
    ("'self'", True), ("'none'", True), ("https:", True), ("data:", True), ("*", True),
    ("https://cdn.example.com", True), ("*.example.com", True), ("example.com:8443", True),
    ("wss://socket.example.com", True), ("'nonce-abc123=='", True), ("'sha256-AbC+/=='", True),
    ("nonce-abc123", False), ("sha256-abc", False), ("bad source", False), ("a;b", False),
    ("", False), ("'unknown'", False)])
def test_valid_source(source, ok):
    assert cb.valid_source(source) is ok


def test_presets_render_exactly():
    assert cb.render(cb.build("api")) == (
        "default-src 'none'; base-uri 'none'; frame-ancestors 'none'")
    assert cb.render(cb.build("basic")) == (
        "default-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'")
    assert cb.render(cb.build("strict")).startswith("default-src 'none'; script-src 'self'")
    assert cb.render(cb.build("strict")).endswith("upgrade-insecure-requests")


def test_every_preset_lints_clean_of_warnings():
    for name in cb.PRESETS:
        warnings = [m for level, m in cb.lint(cb.build(name)) if level == "warning"]
        assert warnings == [], name


def test_allow_adds_sources_and_creates_directives():
    policy = cb.build("basic", ["script-src=https://cdn.example.com,self", "img-src=data:"])
    assert policy["script-src"] == ["https://cdn.example.com", "'self'"]  # bare 'self' is quoted
    assert policy["img-src"] == ["data:"]
    again = cb.build("basic", ["default-src=https://a.example", "default-src=https://a.example"])
    assert again["default-src"] == ["'self'", "https://a.example"]  # no duplicates


def test_none_handling():
    assert cb.build("basic", ["script-src=none"])["script-src"] == ["'none'"]
    policy = cb.build("strict", ["default-src=https://x.example"])
    assert policy["default-src"] == ["https://x.example"]  # 'none' is replaced, not mixed
    assert cb.build("strict", ["script-src=none"])["script-src"] == ["'none'"]


def test_remove_report_uri_and_strict_dynamic():
    policy = cb.build("strict", removes=["img-src", "FONT-SRC"], report_uri="/csp-reports",
                      strict_dynamic=True)
    assert "img-src" not in policy and "font-src" not in policy
    assert policy["report-uri"] == ["/csp-reports"]
    assert policy["script-src"] == ["'self'", "'strict-dynamic'"]


def test_nonce_goes_on_script_and_style():
    policy = cb.build("strict", nonce=True)
    assert policy["script-src"] == ["'self'", "'nonce-{{nonce}}'"]
    assert policy["style-src"] == ["'self'", "'nonce-{{nonce}}'"]
    api = cb.build("api", nonce=True)
    assert api["script-src"] == ["'self'", "'nonce-{{nonce}}'"] and "style-src" not in api


@pytest.mark.parametrize("allow", ["script-src", "script-src=", "colour-src=self",
                                   "script-src=bad source;x", "upgrade-insecure-requests=self",
                                   "script-src=nonce-abc"])
def test_bad_allow_values(allow):
    with pytest.raises(ValueError):
        cb.build("basic", [allow])


def test_bad_report_uri():
    with pytest.raises(ValueError):
        cb.build("basic", report_uri="javascript:alert(1)")


def test_lint_finds_the_classic_mistakes():
    policy = {"default-src": ["*"], "script-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'",
                                                  "data:"], "img-src": ["http:"],
              "style-src": ["'none'", "'self'"]}
    messages = " | ".join(m for _, m in cb.lint(policy))
    for expected in ("'unsafe-inline' with no nonce", "'unsafe-eval'", "any host with *",
                     "plain http:", "data: URLs", "mixes 'none'", "object-src isn't restricted",
                     "base-uri is missing"):
        assert expected in messages
    fine = {"default-src": ["'self'"], "script-src": ["'self'", "'unsafe-inline'", "'nonce-x'"],
            "object-src": ["'none'"], "base-uri": ["'self'"], "frame-ancestors": ["'none'"]}
    assert cb.lint(fine) == []
    assert ("info", "no default-src, so directives you didn't list are unrestricted") in cb.lint({})


def test_output_formats():
    policy = cb.build("api")
    value = "default-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    assert cb.output(policy, "header", False) == f"Content-Security-Policy: {value}"
    assert cb.output(policy, "header", True).startswith("Content-Security-Policy-Report-Only:")
    nginx = cb.output(policy, "nginx", False)
    assert nginx == f'add_header Content-Security-Policy "{value}" always;'
    apache = cb.output(policy, "apache", False)
    assert apache == f'Header always set Content-Security-Policy "{value}"'
    assert cb.output(policy, "express", False) == (
        f"res.setHeader('Content-Security-Policy', \"{value}\");")
    data = json.loads(cb.output(policy, "json", False))
    assert data["directives"]["default-src"] == ["'none'"]


def test_meta_drops_directives_it_cannot_carry():
    text = cb.output(cb.build("api"), "meta", False)
    assert '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; ' \
           'base-uri \'none\'">' in text
    assert "can't carry frame-ancestors" in text


def test_interactive_walkthrough():
    answers = iter(["strict", "https://cdn.example.com", "", "https://api.example.com", "", "",
                    "y", "/reports"])
    choices = cb.interactive(lambda prompt: next(answers))
    assert choices == {"preset": "strict", "nonce": True, "report_uri": "/reports",
                       "allows": ["script-src=https://cdn.example.com",
                                  "connect-src=https://api.example.com"]}
    with pytest.raises(ValueError, match="unknown preset"):
        cb.interactive(lambda prompt: "wild")
    assert cb.interactive(lambda prompt: "")["preset"] == "balanced"


def test_cli(capsys):
    assert cb.main(["--preset", "strict", "--allow", "script-src=https://cdn.example.com",
                    "--nonce"]) == 0
    captured = capsys.readouterr()
    assert captured.out.startswith("Content-Security-Policy: default-src 'none'; script-src 'self'")
    assert "'nonce-{{nonce}}'" in captured.out and "replace {{nonce}}" in captured.err
    assert cb.main(["--preset", "basic", "--allow", "script-src=*", "--strict"]) == 1
    assert "warning: script-src allows any host" in capsys.readouterr().err
    assert cb.main(["--preset", "api", "--report-only"]) == 0
    assert "Report-Only logs problems" in capsys.readouterr().err
    assert cb.main(["--allow", "nonsense"]) == 1
    assert "Error:" in capsys.readouterr().err


def test_cli_interactive(capsys):
    answers = iter(["basic", "", "", "", "", "", "n", ""])
    assert cb.main(["--interactive"], ask=lambda prompt: next(answers)) == 0
    assert "default-src 'self'; object-src 'none'" in capsys.readouterr().out
