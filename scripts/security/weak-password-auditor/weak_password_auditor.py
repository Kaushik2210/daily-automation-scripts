"""Audit your own password list, offline, for reuse and weakness. It never prints a password."""
import argparse
import csv
import io
import json
import math
import re
import string
import sys
from pathlib import Path

COMMON = set("""123456 password 12345678 qwerty 123456789 12345 1234 111111 1234567 dragon 123123
baseball abc123 football monkey letmein 696969 shadow master 666666 qwertyuiop 123321 mustang
1234567890 michael 654321 superman 1qaz2wsx 7777777 121212 000000 qazwsx 123qwe killer trustno1
jordan jennifer zxcvbnm asdfgh hunter buster soccer harley batman andrew tigger sunshine iloveyou
2000 charlie robert thomas hockey ranger daniel starwars klaster 112233 george computer michelle
jessica pepper 1111 zxcvbn 555555 11111111 131313 freedom 777777 pass maggie 159753 aaaaaa ginger
princess joshua cheese amanda summer love ashley nicole chelsea biteme matthew access yankees
987654321 dallas austin thunder taylor matrix welcome admin password1 password123 passw0rd
changeme letmein123 qwerty123 admin123 welcome1 login guest root toor test secret""".split())  # noqa: SIM905
WALKS = ["qwert", "werty", "ertyu", "asdfg", "sdfgh", "zxcvb", "xcvbn", "qazws", "1qaz2",
         "12345", "23456", "34567", "45678", "56789", "67890", "abcde", "bcdef", "cdefg", "poiuy",
         "lkjhg", "mnbvc", "09876", "98765", "87654"]
SEASONS = ["spring", "summer", "autumn", "fall", "winter"]
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september",
          "october", "november", "december"]
SEVERITY = {"critical": 3, "weak": 2, "fair": 1, "strong": 0}


def pool_size(password):
    pool = 0
    for chars, size in ((string.ascii_lowercase, 26), (string.ascii_uppercase, 26),
                        (string.digits, 10)):
        pool += size if any(c in chars for c in password) else 0
    if any(not c.isalnum() for c in password):
        pool += 33
    return pool or 1


def entropy_bits(password):
    """A rough upper bound: length * log2(character pool). Real guessing is often easier."""
    return len(password) * math.log2(pool_size(password))


def base_of(password):
    """The password with trailing digits and symbols removed: 'Summer2025!' -> 'summer'."""
    return re.sub(r"[\d\W_]+$", "", password).lower()


def problems(password, label=""):
    """[(severity, message)] for one password. Reuse is judged separately across the list."""
    found = []
    lowered = password.lower()
    if lowered in COMMON or base_of(password) in COMMON and len(base_of(password)) >= 4:
        found.append(("critical", "is a very common password"))
    if len(password) < 8:
        found.append(("critical", f"is only {len(password)} characters long"))
    elif len(password) < 12:
        found.append(("weak", f"is short ({len(password)} characters; 12 or more is better)"))
    if any(w in lowered for w in WALKS):
        found.append(("weak", "contains a keyboard or number sequence"))
    if re.search(r"(.)\1{3,}", password) or re.fullmatch(r"(.{1,3})\1{2,}", password):
        found.append(("weak", "repeats the same characters"))
    if re.search(r"(19|20)\d\d", password) and len(re.sub(r"[^A-Za-z]", "", password)) <= 10:
        found.append(("weak", "is a word followed by a year"))
    if re.match(r"(" + "|".join(SEASONS + MONTHS) + r")[\W_]*\d", lowered):
        found.append(("weak", "is a season or month plus numbers"))
    words = {w for w in re.split(r"[\W_]+", label.lower()) if len(w) >= 4}
    if any(w in lowered for w in words):
        found.append(("weak", "contains the site or account name"))
    if not found and entropy_bits(password) < 45:
        found.append(("weak", "has few kinds of characters for its length"))
    classes = sum(any(f(c) for c in password) for f in
                  (str.islower, str.isupper, str.isdigit, lambda c: not c.isalnum()))
    if not found and classes < 3:
        found.append(("fair", "uses only letters or only digits; mix more character types"))
    return found


def score(password, issues, reused):
    bits = min(entropy_bits(password), 100)
    value = bits
    for severity, _ in issues:
        value -= {"critical": 60, "weak": 30, "fair": 10}[severity]
    if reused:
        value -= 40
    return max(0, min(100, round(value)))


def rating(issues, reused):
    worst = max((SEVERITY[s] for s, _ in issues), default=0)
    if reused:
        worst = max(worst, SEVERITY["critical"])
    return {3: "critical", 2: "weak", 1: "fair", 0: "strong"}[worst]


def mask(password):
    return f"{password[:1]}{'*' * min(max(len(password) - 1, 0), 10)} ({len(password)} chars)"


def read_entries(text, password_column, label_column):
    """CSV with a password column, or one password per line. Returns [(label, password)]."""
    first = text.splitlines()[0] if text.strip() else ""
    if "," in first and password_column.lower() in [c.strip().lower() for c in first.split(",")]:
        reader = csv.DictReader(io.StringIO(text))
        names = {n.lower(): n for n in reader.fieldnames or []}
        pw = names[password_column.lower()]
        label = names.get((label_column or "").lower()) or next(
            (n for n in reader.fieldnames if n != pw), None)
        return [((row.get(label) or f"row {n}").strip(), row[pw]) for n, row in
                enumerate(reader, 1) if row.get(pw)]
    return [(f"line {n}", line.rstrip("\r\n")) for n, line in enumerate(text.splitlines(), 1)
            if line.strip()]


def audit(entries):
    """Return the list of per-entry results plus the reuse groups."""
    by_password, by_base = {}, {}
    for label, password in entries:
        by_password.setdefault(password, []).append(label)
        stem = base_of(password)
        if len(stem) >= 4:
            by_base.setdefault(stem, set()).add(password)
    results = []
    for label, password in entries:
        reused = len(by_password[password]) > 1
        issues = problems(password, label)
        stem = base_of(password)
        variants = len(by_base.get(stem, ())) > 1
        if variants:
            issues.append(("weak", "is one of several variations of the same base word"))
        results.append({"label": label, "password": password, "issues": issues, "reused": reused,
                        "rating": rating(issues, reused), "score": score(password, issues, reused)})
    groups = [sorted(labels) for labels in by_password.values() if len(labels) > 1]
    return results, groups


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit a password list for reuse and weakness.")
    parser.add_argument("file", type=Path,
                        help="CSV with a password column, or one password per line")
    parser.add_argument("--password-column", default="password", help="CSV column (password)")
    parser.add_argument("--label-column",
                        help="CSV column naming each account (default: the first other column)")
    parser.add_argument("--fail-on", choices=["none", "fair", "weak", "critical"],
                        default="none", help="exit 1 if any entry is at least this bad (none)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)
    try:
        entries = read_entries(args.file.read_text(encoding="utf-8-sig"), args.password_column,
                               args.label_column)
    except (OSError, UnicodeDecodeError, KeyError) as err:
        print(f"Can't read the list: {err}", file=sys.stderr)
        return 1
    if not entries:
        print("No passwords found in that file.", file=sys.stderr)
        return 1
    results, groups = audit(entries)
    counts = {name: sum(r["rating"] == name for r in results)
              for name in ("critical", "weak", "fair", "strong")}
    if args.format == "json":
        print(json.dumps({"counts": counts, "reuse_groups": groups, "entries": [
            {"label": r["label"], "password": mask(r["password"]), "rating": r["rating"],
             "score": r["score"], "reused": r["reused"], "problems": [m for _, m in r["issues"]]}
            for r in results]}, indent=1))
    else:
        print(f"Audited {len(results)} password(s). Nothing was sent anywhere, and no full "
              "password is shown below.\n")
        print(", ".join(f"{n} {name}" for name, n in counts.items()) + "\n")
        for r in sorted(results, key=lambda r: (-SEVERITY[r["rating"]], r["score"], r["label"])):
            if r["rating"] == "strong":
                continue
            print(f"[{r['rating'].upper()}] {r['label']}  {mask(r['password'])}  "
                  f"score {r['score']}")
            notes = [m for _, m in r["issues"]] + (["is used for more than one account"]
                                                  if r["reused"] else [])
            print("    " + "; ".join(notes))
        if groups:
            print("\nReused passwords:")
            print("\n".join(f"  {len(g)} accounts share one password: {', '.join(g)}"
                            for g in groups))
        print("\nWhat to do: change the critical ones first, give every account its own long\n"
              "random password (a password manager helps), and turn on two-factor sign-in.")
    limit = SEVERITY.get(args.fail_on)
    bad = args.fail_on != "none" and any(SEVERITY[r["rating"]] >= limit for r in results)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
