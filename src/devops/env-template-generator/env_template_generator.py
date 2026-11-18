"""Make a .env.example from a real .env: same keys and comments, secret values removed."""
import argparse
import re
import sys
from pathlib import Path

LINE = re.compile(r"^(\s*(?:export\s+)?)([A-Za-z_][A-Za-z0-9_.]*)(\s*=\s*)(.*)$")
SECRET = re.compile(r"PASS|SECRET|TOKEN|KEY|PRIVATE|CREDENTIAL|AUTH|SALT|SIGNATURE|DSN",
                    re.IGNORECASE)
SAFE_VALUE = re.compile(
    r"^(true|false|yes|no|on|off|\d{1,5}|[a-z]{2,12}|localhost|0\.0\.0\.0|127\.0\.0\.1)$",
    re.IGNORECASE)


def unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value.split(" #", 1)[0].strip()


def is_secret(key, value):
    return bool(SECRET.search(key)) or bool(re.search(r"://[^/\s:@]+:[^/\s@]+@", value))


def convert(text, keep_safe=False, placeholder=""):
    """Return (template text, [keys in order], [keys whose values were removed])."""
    out, keys, blanked = [], [], []
    for line in text.replace("\r\n", "\n").split("\n"):
        match = LINE.match(line)
        if not match:
            out.append(line)
            continue
        prefix, key, equals, raw = match.groups()
        value = unquote(raw)
        keys.append(key)
        keep = keep_safe and value and not is_secret(key, value) and SAFE_VALUE.match(value)
        if keep:
            out.append(f"{prefix}{key}{equals}{raw.strip()}")
        else:
            out.append(f"{prefix}{key}{equals}{placeholder}")
            if value:
                blanked.append(key)
    return "\n".join(out).rstrip("\n") + "\n", keys, blanked


def keys_in(text):
    return [m.group(2) for line in text.splitlines() if (m := LINE.match(line))]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Create a .env.example from a .env file.")
    parser.add_argument("env_file", type=Path)
    parser.add_argument("-o", "--output", type=Path,
                        help="file to create (default: <env file>.example next to it)")
    parser.add_argument("--keep-safe", action="store_true",
                        help="keep harmless values (true/false, port numbers, localhost...)")
    parser.add_argument("--placeholder", default="", help="text to put after each = (empty)")
    parser.add_argument("--apply", action="store_true",
                        help="really write the file (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.env_file.is_file():
        parser.error(f"not a file: {args.env_file}")

    template, keys, blanked = convert(args.env_file.read_text(encoding="utf-8", errors="replace"),
                                      args.keep_safe, args.placeholder)
    output = args.output or args.env_file.with_name(args.env_file.name + ".example")
    print(f"{args.env_file.name}: {len(keys)} variable(s), {len(blanked)} value(s) removed\n")
    print(template, end="")
    status = 0
    if output.exists():
        existing = set(keys_in(output.read_text(encoding="utf-8", errors="replace")))
        missing = [k for k in keys if k not in existing]
        extra = sorted(existing - set(keys))
        print(f"\n{output.name} already exists and was not touched.")
        if missing:
            print(f"  Missing from it: {', '.join(missing)}")
            status = 1
        if extra:
            print(f"  Only in it (not in {args.env_file.name}): {', '.join(extra)}")
        if not missing and not extra:
            print("  It lists exactly the same variables.")
        return status
    if not args.apply:
        print(f"\nDry run. Use --apply to write {output.name}.")
        return 0
    output.write_text(template, encoding="utf-8")
    print(f"\nSaved {output}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
