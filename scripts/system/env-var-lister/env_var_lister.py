"""List and search environment variables, masking anything that looks like a secret."""
import argparse
import os
import re
import sys

SECRET_WORDS = "KEY|TOKEN|SECRET|PASSWORD|PASSWD|PWD|CREDENTIAL|AUTH|COOKIE"
SECRET_RE = re.compile(f"({SECRET_WORDS})", re.IGNORECASE)


def is_secret(name):
    return bool(SECRET_RE.search(name))


def mask(value):
    """Keep a hint of the value's length without revealing it."""
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}{'*' * min(len(value) - 4, 12)}{value[-2:]}"


def list_vars(environ, search="", show_secrets=False):
    """Return sorted (name, display_value) pairs whose name or value matches `search`."""
    needle = search.lower()
    rows = []
    for name, value in sorted(environ.items(), key=lambda item: item[0].lower()):
        if needle and needle not in name.lower() and needle not in value.lower():
            continue
        hidden = is_secret(name) and not show_secrets
        rows.append((name, mask(value) if hidden else value))
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description="List environment variables safely.")
    parser.add_argument("search", nargs="?", default="",
                        help="only show names or values containing this")
    parser.add_argument("--show-secrets", action="store_true",
                        help="don't mask values of KEY, TOKEN, SECRET, PASSWORD ... variables")
    parser.add_argument("--names-only", action="store_true", help="print names without values")
    args = parser.parse_args(argv)

    rows = list_vars(os.environ, args.search, args.show_secrets)
    for name, value in rows:
        print(name if args.names_only else f"{name}={value}")
    print(f"{len(rows)} variable(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
