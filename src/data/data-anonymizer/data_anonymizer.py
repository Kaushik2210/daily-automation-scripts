"""Mask emails, names, phone numbers and other personal data in a CSV file."""
import argparse
import csv
import hashlib
import re
import sys
from pathlib import Path

FIRST = ["Alex", "Blake", "Casey", "Dana", "Eden", "Finn", "Gray", "Harper", "Indy", "Jules",
         "Kai", "Lane", "Morgan", "Noor", "Orion", "Parker", "Quinn", "Reese", "Sage", "Taylor"]
LAST = ["Adler", "Brooks", "Carver", "Dalton", "Ellis", "Foster", "Grant", "Hayes", "Irving",
        "Jensen", "Keller", "Lowe", "Mercer", "Nolan", "Oakes", "Porter", "Quill", "Rowe",
        "Stone", "Tate"]
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?<![\w])\+?\d[\d\s().-]{6,}\d(?![\w])")
HEADER_KINDS = [  # (regex on the header, kind)
    (r"e-?mail", "email"), (r"phone|mobile|\btel\b|cell|fax", "phone"),
    (r"(^|_)(first|last|full|sur|customer|user|contact)?_?name$|surname", "name"),
    (r"(^|_)ip(_?addr(ess)?)?$", "ip"), (r"card|\bpan\b", "card"),
    (r"ssn|aadhaar|passport|national_?id|tax_?id", "redact"),
]
KINDS = ["email", "name", "phone", "card", "ip", "hash", "redact", "year", "scrub"]


def digest(value, salt, kind):
    return int(hashlib.sha256(f"{salt}|{kind}|{value.strip().lower()}".encode()).hexdigest(), 16)


def mask(value, kind, salt):
    """Return the masked version of one non-empty value. Equal inputs give equal outputs."""
    number = digest(value, salt, kind)
    if kind == "email":
        return f"user_{number % 16 ** 8:08x}@example.com"
    if kind == "name":
        return f"{FIRST[number % len(FIRST)]} {LAST[(number >> 16) % len(LAST)]}"
    if kind == "phone":
        total = sum(c.isdigit() for c in value)
        seen = 0
        out = []
        for char in value:
            if char.isdigit():
                seen += 1
                out.append(char if seen > total - 2 else "X")
            else:
                out.append(char)
        return "".join(out)
    if kind == "card":
        digits = re.sub(r"\D", "", value)
        return f"**** **** **** {digits[-4:]}"
    if kind == "ip":
        return f"10.{number % 256}.{(number >> 8) % 256}.{(number >> 16) % 256}"
    if kind == "hash":
        return f"{number % 16 ** 10:010x}"
    if kind == "year":
        match = re.search(r"\d{4}", value)
        return match.group(0) if match else "[date]"
    if kind == "scrub":
        return PHONE.sub("[phone]", EMAIL.sub("[email]", value))
    return "[REDACTED]"


def detect(header, rows):
    """Guess the kind of personal data for each column from its name and its values."""
    found = {}
    for index, name in enumerate(header):
        label = name.strip().lower().replace(" ", "_")
        kind = next((k for pattern, k in HEADER_KINDS if re.search(pattern, label)), None)
        if kind is None:
            values = [r[index] for r in rows if index < len(r) and r[index].strip()]
            if len(values) >= 3 and sum(bool(re.fullmatch(EMAIL, v.strip()))
                                        for v in values) >= 0.8 * len(values):
                kind = "email"
        if kind:
            found[name] = kind
    return found


def anonymise(header, rows, plan, salt):
    """Return (new rows, number of values changed per column)."""
    changed = dict.fromkeys(plan, 0)
    result = []
    for row in rows:
        row = list(row) + [""] * (len(header) - len(row))
        for name, kind in plan.items():
            index = header.index(name)
            if row[index].strip():
                masked = mask(row[index], kind, salt)
                changed[name] += masked != row[index]
                row[index] = masked
        result.append(row)
    return result, changed


def main(argv=None):
    parser = argparse.ArgumentParser(description="Mask personal data in a CSV file.")
    parser.add_argument("csv", type=Path)
    parser.add_argument("--mask", action="append", default=[], metavar="COLUMN:KIND",
                        help=f"mask this column as one of: {', '.join(KINDS)}")
    parser.add_argument("--keep", action="append", default=[], metavar="COLUMN",
                        help="never mask this column, even if it looks personal")
    parser.add_argument("--no-auto", action="store_true", help="only mask what --mask names")
    parser.add_argument("--salt", default="anon", help="secret text that makes the masking yours")
    parser.add_argument("-o", "--output", type=Path,
                        help="file to create (default: NAME.anonymized.csv)")
    parser.add_argument("--apply", action="store_true",
                        help="really write the file (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.csv.is_file():
        parser.error(f"not a file: {args.csv}")

    with args.csv.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
        rows = [r for r in reader if r]
    if not header:
        print("The CSV file is empty.", file=sys.stderr)
        return 1
    plan = {} if args.no_auto else detect(header, rows)
    for name in args.keep:
        plan.pop(name, None)
    explicit = set()
    for item in args.mask:
        column, _, kind = item.rpartition(":")
        if column not in header or kind not in KINDS:
            parser.error(f"--mask needs COLUMN:KIND with a real column and a kind of "
                         f"{', '.join(KINDS)} (got '{item}')")
        plan[column] = kind
        explicit.add(column)
    if not plan:
        print("No personal-data columns found. Name them with --mask COLUMN:KIND.")
        return 1

    masked, changed = anonymise(header, rows, plan, args.salt)
    print(f"{args.csv.name}: {len(rows)} row(s), {len(plan)} column(s) to mask")
    for name, kind in plan.items():
        how = "chosen" if name in explicit else "detected"
        print(f"  {name:<14} as {kind:<7} ({how}) - {changed[name]} value(s) changed")
    print("\nPreview (first rows):")
    indexes = [header.index(n) for n in plan]
    for before, after in list(zip(rows, masked, strict=True))[:3]:
        for index in indexes[:3]:
            old = before[index] if index < len(before) else ""
            print(f"  {header[index]:<12} {old!r:<28} -> {after[index]!r}")
        print()
    output = args.output or args.csv.with_name(f"{args.csv.stem}.anonymized.csv")
    if not args.apply:
        print(f"Dry run. Use --apply to write {output.name}.")
        return 0
    if output.exists():
        print(f"{output} already exists; choose another name with -o.", file=sys.stderr)
        return 1
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(masked)
    print(f"Saved {output}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
