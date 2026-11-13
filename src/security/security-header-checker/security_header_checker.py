"""Grade a website's HTTP security headers (A+ to F) and explain how to improve them."""
import argparse
import re
import sys
import urllib.error  # web-ok: the network is only used for live URLs; --headers files work anywhere
import urllib.request
from pathlib import Path

GRADES = [(95, "A+"), (85, "A"), (70, "B"), (55, "C"), (40, "D"), (0, "F")]
ORDER = ["A+", "A", "B", "C", "D", "F"]
STRONG_REFERRER = {"no-referrer", "same-origin", "strict-origin", "strict-origin-when-cross-origin",
                   "origin-when-cross-origin", "origin"}


def parse_headers(text):
    """Parse a raw header dump (curl -I style). With redirects, the last response is used."""
    blocks, current = [], []
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.startswith("HTTP/"):
            if current:
                blocks.append(current)
            current = []
        elif ":" in line and not line.startswith((" ", "\t")):
            current.append(tuple(part.strip() for part in line.split(":", 1)))
    if current:
        blocks.append(current)
    headers = {}
    for name, value in (blocks[-1] if blocks else []):
        headers.setdefault(name.lower(), []).append(value)
    return headers


def fetch_headers(url, timeout=15):
    request = urllib.request.Request(url, headers={"User-Agent": "daily-automation-scripts/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        headers = {}
        for name, value in response.headers.items():
            headers.setdefault(name.lower(), []).append(value)
        return headers


def first(headers, name):
    return (headers.get(name) or [""])[0]


def check_hsts(headers):
    value = first(headers, "strict-transport-security")
    if not value:
        return 0, 20, "FAIL", "No Strict-Transport-Security: browsers may use plain HTTP first"
    match = re.search(r"max-age=(\d+)", value, re.IGNORECASE)
    age = int(match.group(1)) if match else 0
    if age < 15552000:
        return 10, 20, "WARN", f"HSTS max-age is only {age}s; use at least 15552000 (6 months)"
    bonus = " with includeSubDomains" if "includesubdomains" in value.lower() else ""
    return 20, 20, "PASS", f"HSTS enabled for {age // 86400} days{bonus}"


def check_csp(headers):
    value = first(headers, "content-security-policy")
    if not value:
        return 0, 25, "FAIL", "No Content-Security-Policy: the best defence against injected code"
    lowered = value.lower()
    problems = [word for word in ("'unsafe-inline'", "'unsafe-eval'") if word in lowered]
    if re.search(r"(script-src|default-src)[^;]*\s\*(\s|;|$)", lowered):
        problems.append("a * wildcard source")
    if problems:
        return 15, 25, "WARN", "CSP allows " + " and ".join(problems) + ", which weakens it"
    return 25, 25, "PASS", "Content-Security-Policy is present with no obviously unsafe sources"


def check_framing(headers):
    xfo = first(headers, "x-frame-options").upper()
    csp = first(headers, "content-security-policy").lower()
    if "frame-ancestors" in csp or xfo in ("DENY", "SAMEORIGIN"):
        return 10, 10, "PASS", "Framing is restricted (clickjacking protection)"
    return 0, 10, "FAIL", "No X-Frame-Options or frame-ancestors: the page can be framed by others"


def check_nosniff(headers):
    if first(headers, "x-content-type-options").lower() == "nosniff":
        return 10, 10, "PASS", "X-Content-Type-Options: nosniff"
    return 0, 10, "FAIL", "Missing X-Content-Type-Options: nosniff"


def check_referrer(headers):
    value = first(headers, "referrer-policy").lower()
    if not value:
        return 0, 10, "FAIL", "No Referrer-Policy: full URLs may leak to other sites"
    if any(part.strip() in STRONG_REFERRER for part in value.split(",")):
        return 10, 10, "PASS", f"Referrer-Policy: {value}"
    return 5, 10, "WARN", f"Referrer-Policy '{value}' still leaks full URLs to other sites"


def check_permissions(headers):
    if first(headers, "permissions-policy"):
        return 5, 5, "PASS", "Permissions-Policy limits browser features"
    return 0, 5, "FAIL", "No Permissions-Policy (camera, microphone, location... aren't restricted)"


def check_isolation(headers):
    have = [n for n in ("cross-origin-opener-policy", "cross-origin-resource-policy")
            if first(headers, n)]
    if len(have) == 2:
        return 5, 5, "PASS", "Cross-origin opener and resource policies set"
    if have:
        return 3, 5, "WARN", f"Only {have[0]} is set; add the other for cross-origin isolation"
    return 0, 5, "FAIL", "No Cross-Origin-Opener-Policy / Cross-Origin-Resource-Policy"


def check_cookies(headers):
    cookies = headers.get("set-cookie", [])
    if not cookies:
        return 10, 10, "PASS", "No cookies are set"
    missing = []
    for cookie in cookies:
        lowered = cookie.lower()
        name = cookie.split("=", 1)[0].strip()
        flags = [flag for flag, word in (("Secure", "secure"), ("HttpOnly", "httponly"),
                                         ("SameSite", "samesite")) if word not in lowered]
        if flags:
            missing.append(f"{name} lacks {'/'.join(flags)}")
    if not missing:
        return 10, 10, "PASS", f"All {len(cookies)} cookie(s) have Secure, HttpOnly and SameSite"
    points = max(0, 10 - 3 * len(missing))
    return points, 10, "WARN" if points else "FAIL", "; ".join(missing)


def check_disclosure(headers):
    leaks = []
    server = first(headers, "server")
    if re.search(r"\d", server):
        leaks.append(f"Server: {server}")
    if first(headers, "x-powered-by"):
        leaks.append(f"X-Powered-By: {first(headers, 'x-powered-by')}")
    if leaks:
        return 0, 5, "WARN", "Reveals software details: " + ", ".join(leaks)
    return 5, 5, "PASS", "No server software versions are advertised"


CHECKS = [("HSTS", check_hsts), ("Content-Security-Policy", check_csp),
          ("Clickjacking", check_framing), ("MIME sniffing", check_nosniff),
          ("Referrer-Policy", check_referrer), ("Permissions-Policy", check_permissions),
          ("Isolation", check_isolation), ("Cookies", check_cookies),
          ("Info disclosure", check_disclosure)]


def grade_for(percent):
    return next(letter for floor, letter in GRADES if percent >= floor)


def evaluate(headers):
    """Return (percent, grade, [(name, status, message, points, maximum)])."""
    results, total, maximum = [], 0, 0
    for name, check in CHECKS:
        points, most, status, message = check(headers)
        total, maximum = total + points, maximum + most
        results.append((name, status, message, points, most))
    percent = round(100 * total / maximum)
    return percent, grade_for(percent), results


def main(argv=None):
    parser = argparse.ArgumentParser(description="Grade a site's security headers.")
    parser.add_argument("source", help="a URL, or a saved header dump (e.g. from curl -I -L)")
    parser.add_argument("--min-grade", choices=ORDER, default="C",
                        help="exit with 1 if the grade is worse than this (C)")
    parser.add_argument("--timeout", type=float, default=15, help="seconds to wait (15)")
    args = parser.parse_args(argv)

    try:
        path = Path(args.source)
        if "://" in args.source:
            headers = fetch_headers(args.source, args.timeout)
        elif path.is_file():
            headers = parse_headers(path.read_text(encoding="utf-8", errors="replace"))
        else:
            parser.error(f"not a URL or a file: {args.source}")
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"Couldn't get the headers: {getattr(err, 'reason', err)}", file=sys.stderr)
        return 1
    if not headers:
        print("No headers found in that input.", file=sys.stderr)
        return 1

    percent, grade, results = evaluate(headers)
    print(f"Security headers: grade {grade} ({percent}%)\n")
    for name, status, message, points, most in results:
        print(f"  [{status}] {name:<24} {points:>2}/{most:<2}  {message}")
    worse = ORDER.index(grade) > ORDER.index(args.min_grade)
    return 1 if worse else 0


if __name__ == "__main__":
    sys.exit(main())
