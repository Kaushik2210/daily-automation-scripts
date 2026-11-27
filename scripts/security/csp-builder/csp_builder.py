"""Build a Content-Security-Policy header from a preset, check it, and print it for your server."""
import argparse
import json
import re
import sys

PRESETS = {
    "strict": {"default-src": ["'none'"], "script-src": ["'self'"], "style-src": ["'self'"],
               "img-src": ["'self'"], "font-src": ["'self'"], "connect-src": ["'self'"],
               "base-uri": ["'self'"], "form-action": ["'self'"], "frame-ancestors": ["'none'"],
               "object-src": ["'none'"], "upgrade-insecure-requests": []},
    "balanced": {"default-src": ["'self'"], "script-src": ["'self'"], "style-src": ["'self'"],
                 "img-src": ["'self'", "data:", "https:"],
                 "font-src": ["'self'", "https:", "data:"],
                 "object-src": ["'none'"], "base-uri": ["'self'"], "form-action": ["'self'"],
                 "frame-ancestors": ["'self'"], "upgrade-insecure-requests": []},
    "basic": {"default-src": ["'self'"], "object-src": ["'none'"], "base-uri": ["'self'"],
              "frame-ancestors": ["'self'"]},
    "api": {"default-src": ["'none'"], "base-uri": ["'none'"], "frame-ancestors": ["'none'"]},
}
FETCH = ["default-src", "script-src", "script-src-elem", "script-src-attr", "style-src",
         "style-src-elem", "style-src-attr", "img-src", "font-src", "connect-src", "media-src",
         "object-src", "frame-src", "child-src", "worker-src", "manifest-src", "prefetch-src"]
OTHER = ["base-uri", "form-action", "frame-ancestors", "sandbox", "report-uri", "report-to",
         "upgrade-insecure-requests", "block-all-mixed-content", "require-trusted-types-for",
         "trusted-types"]
KNOWN = FETCH + OTHER
FLAG_ONLY = {"upgrade-insecure-requests", "block-all-mixed-content"}
KEYWORDS = {"'self'", "'none'", "'unsafe-inline'", "'unsafe-eval'", "'strict-dynamic'",
            "'unsafe-hashes'", "'wasm-unsafe-eval'", "'report-sample'"}
HASHED = re.compile(r"^'(nonce|sha256|sha384|sha512)-[A-Za-z0-9+/=_{}.-]+'$")
SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:$")
HOST = re.compile(r"^(https?://|wss?://)?(\*\.)?[A-Za-z0-9.-]+(:(\d+|\*))?(/[^\s;,]*)?$")
META_UNSUPPORTED = {"frame-ancestors", "report-uri", "report-to", "sandbox"}


def valid_source(source):
    if re.match(r"^(nonce|sha256|sha384|sha512)-", source):
        return False  # these must be quoted, or they would be read as host names
    return (source in KEYWORDS or source == "*" or bool(HASHED.match(source))
            or bool(SCHEME.match(source)) or bool(HOST.match(source)))


def build(preset, allows=(), removes=(), nonce=False, strict_dynamic=False, report_uri=None):
    """Return an ordered {directive: [sources]} dict. Raises ValueError for bad input."""
    policy = {k: list(v) for k, v in PRESETS[preset].items()}
    for directive in removes:
        policy.pop(directive.strip().lower(), None)
    for item in allows:
        directive, sep, sources = item.partition("=")
        directive = directive.strip().lower()
        if not sep or not sources.strip():
            raise ValueError(f"--allow needs DIRECTIVE=source[,source], got '{item}'")
        if directive not in KNOWN:
            raise ValueError(f"unknown directive '{directive}'")
        values = [s for s in re.split(r"[,\s]+", sources.strip()) if s]
        values = [f"'{v}'" if v in {k.strip("'") for k in KEYWORDS} else v for v in values]
        for source in values:
            if not valid_source(source):
                raise ValueError(f"'{source}' isn't a valid source (in {directive})")
        if directive in FLAG_ONLY:
            raise ValueError(f"{directive} takes no sources")
        current = policy.setdefault(directive, [])
        if values == ["'none'"]:
            current[:] = ["'none'"]
            continue
        if current == ["'none'"]:
            current.clear()
        current.extend(v for v in values if v not in current)
    if nonce:
        policy.setdefault("script-src", ["'self'"])
        for directive in ("script-src", "style-src"):
            if directive in policy:
                if policy[directive] == ["'none'"]:
                    policy[directive] = []
                policy[directive].append("'nonce-{{nonce}}'")
    if strict_dynamic:
        policy.setdefault("script-src", [])
        if "'strict-dynamic'" not in policy["script-src"]:
            policy["script-src"].append("'strict-dynamic'")
    if report_uri:
        if not re.match(r"^(https?://\S+|/\S*)$", report_uri):
            raise ValueError("--report-uri should be an http(s) address or a path")
        policy["report-uri"] = [report_uri]
    return policy


def render(policy):
    return "; ".join(" ".join([d, *s]) for d, s in policy.items())


def lint(policy):
    """[(level, message)] where level is 'warning' or 'info'."""
    notes = []
    script = policy.get("script-src", policy.get("default-src", []))
    if "'unsafe-inline'" in script and not any(s.startswith("'nonce-") or s.startswith("'sha")
                                                for s in script):
        notes.append(("warning", "script-src allows 'unsafe-inline' with no nonce or hash, which "
                      "removes most of the protection against injected scripts"))
    for directive, sources in policy.items():
        if "'unsafe-eval'" in sources:
            notes.append(("warning", f"{directive} allows 'unsafe-eval' (eval and similar)"))
        if "*" in sources:
            notes.append(("warning", f"{directive} allows any host with *"))
        if "http:" in sources:
            notes.append(("warning", f"{directive} allows plain http: sources"))
        if "data:" in sources and directive in ("script-src", "default-src", "script-src-elem"):
            notes.append(("warning", f"{directive} allows data: URLs, which can carry script"))
        if "'none'" in sources and len(sources) > 1:
            notes.append(("warning", f"{directive} mixes 'none' with other sources; "
                                     "'none' makes the rest pointless"))
    if "object-src" not in policy and policy.get("default-src") != ["'none'"]:
        notes.append(("warning", "object-src isn't restricted; add object-src 'none'"))
    if "base-uri" not in policy:
        notes.append(("warning", "base-uri is missing; an injected <base> tag could redirect "
                                 "relative links"))
    if "frame-ancestors" not in policy:
        notes.append(("info", "frame-ancestors is missing, so other sites can frame your pages"))
    if "default-src" not in policy:
        notes.append(("info", "no default-src, so directives you didn't list are unrestricted"))
    if any(s.startswith("'nonce-{{") for srcs in policy.values() for s in srcs):
        notes.append(("info", "replace {{nonce}} with a fresh random value on every response, "
                              "and put the same value on your <script nonce=...> tags"))
    return notes


def output(policy, fmt, report_only):
    name = "Content-Security-Policy-Report-Only" if report_only else "Content-Security-Policy"
    value = render(policy)
    if fmt == "header":
        return f"{name}: {value}"
    if fmt == "meta":
        dropped = sorted(META_UNSUPPORTED & set(policy))
        kept = render({d: s for d, s in policy.items() if d not in META_UNSUPPORTED})
        extra = (f"\n<!-- a <meta> tag can't carry {', '.join(dropped)}; set those in the HTTP "
                 "header -->" if dropped else "")
        return f'<meta http-equiv="{name}" content="{kept}">{extra}'
    if fmt == "nginx":
        return f"add_header {name} \"{value}\" always;"
    if fmt == "apache":
        return f'Header always set {name} "{value}"'
    if fmt == "express":
        return f"res.setHeader('{name}', {json.dumps(value)});"
    return json.dumps({name: value, "directives": policy}, indent=2)


QUESTIONS = [
    ("script-src", "Extra hosts allowed to run scripts (e.g. https://cdn.example.com)"),
    ("style-src", "Extra hosts for stylesheets"),
    ("connect-src", "Hosts your page sends requests to (APIs, websockets)"),
    ("img-src", "Extra hosts for images"),
    ("frame-src", "Sites you embed in frames (e.g. https://www.youtube.com)")]


def interactive(ask=input):
    """Ask a few questions and return the build() arguments."""
    print("Answer a few questions (press Enter for the suggestion).")
    preset = ask("Starting point: strict, balanced, basic or api [balanced]: ").strip()
    preset = preset or "balanced"
    if preset not in PRESETS:
        raise ValueError(f"unknown preset '{preset}'")
    allows = []
    for directive, question in QUESTIONS:
        answer = ask(f"{question}, comma separated, or blank: ").strip()
        if answer:
            allows.append(f"{directive}={answer}")
    inline = ask("Do you use inline scripts you control (adds a nonce)? [y/N]: ")
    report = ask("Report violations to this address, or blank: ").strip() or None
    return {"preset": preset, "allows": allows, "nonce": inline.strip().lower() == "y",
            "report_uri": report}


def main(argv=None, ask=input):
    parser = argparse.ArgumentParser(description="Build a Content-Security-Policy header.")
    parser.add_argument("--preset", choices=sorted(PRESETS), default="balanced",
                        help="starting policy (balanced)")
    parser.add_argument("--allow", action="append", default=[], metavar="DIRECTIVE=SOURCE,...",
                        help="add sources, e.g. script-src=https://cdn.example.com (repeatable)")
    parser.add_argument("--remove", action="append", default=[], metavar="DIRECTIVE",
                        help="drop a directive from the preset (repeatable)")
    parser.add_argument("--nonce", action="store_true", help="add a 'nonce-{{nonce}}' placeholder")
    parser.add_argument("--strict-dynamic", action="store_true", help="add 'strict-dynamic'")
    parser.add_argument("--report-uri", help="where browsers send violation reports")
    parser.add_argument("--report-only", action="store_true",
                        help="use the Report-Only header: log violations without blocking")
    parser.add_argument("--format", default="header",
                        choices=["header", "meta", "nginx", "apache", "express", "json"])
    parser.add_argument("--interactive", action="store_true", help="answer questions instead")
    parser.add_argument("--strict", action="store_true", help="exit 1 if there are any warnings")
    args = parser.parse_args(argv)
    try:
        if args.interactive:
            choices = interactive(ask)
            policy = build(choices["preset"], choices["allows"], (), choices["nonce"], False,
                           choices["report_uri"])
        else:
            policy = build(args.preset, args.allow, args.remove, args.nonce, args.strict_dynamic,
                           args.report_uri)
    except ValueError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1
    print(output(policy, args.format, args.report_only))
    notes = lint(policy)
    for level, message in notes:
        print(f"{level}: {message}", file=sys.stderr)
    if args.report_only:
        print("note: Report-Only logs problems without blocking anything; switch to the real "
              "header once the reports are clean.", file=sys.stderr)
    return 1 if args.strict and any(level == "warning" for level, _ in notes) else 0


if __name__ == "__main__":
    sys.exit(main())
