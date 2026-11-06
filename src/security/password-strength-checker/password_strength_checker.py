"""Score a password and explain what makes it weak. The password is never echoed."""
import argparse
import getpass
import math
import re
import sys

COMMON = {
    "password", "123456", "12345678", "qwerty", "abc123", "letmein", "welcome", "admin",
    "iloveyou", "monkey", "dragon", "football", "baseball", "master", "sunshine", "princess",
    "login", "passw0rd", "starwars", "trustno1", "111111", "123123", "000000", "qwertyuiop",
}
KEYBOARD_ROWS = ["qwertyuiop", "asdfghjkl", "zxcvbnm", "1234567890"]
LABELS = ["very weak", "weak", "fair", "strong", "very strong"]


def pool_size(password):
    pool = 0
    for pattern, size in ((r"[a-z]", 26), (r"[A-Z]", 26), (r"[0-9]", 10), (r"[^A-Za-z0-9]", 33)):
        if re.search(pattern, password):
            pool += size
    return pool


def entropy_bits(password):
    """Rough upper bound: length * log2(character pool)."""
    pool = pool_size(password)
    return len(password) * math.log2(pool) if pool else 0.0


def has_sequence(password, length=4):
    """True if the password holds a run like 'abcd', '4321' or 'qwer'."""
    lowered = password.lower()
    sources = [*KEYBOARD_ROWS, "abcdefghijklmnopqrstuvwxyz", "0123456789"]
    for source in sources:
        for text in (source, source[::-1]):
            for i in range(len(text) - length + 1):
                if text[i:i + length] in lowered:
                    return True
    return False


def analyze(password):
    """Return (score 0-4, list of problems)."""
    problems = []
    lowered = password.lower()
    if lowered in COMMON or lowered.rstrip("0123456789!") in COMMON:
        problems.append("is a very common password")
    if len(password) < 12:
        problems.append(f"is short ({len(password)} characters; aim for 12 or more)")
    if re.search(r"(.)\1{2,}", password):
        problems.append("repeats the same character three or more times")
    if has_sequence(password):
        problems.append("contains an easy sequence such as abcd, 1234 or qwer")
    if pool_size(password) < 52 and len(password) < 16:
        problems.append("mixes too few kinds of characters (use upper, lower, digits, symbols)")
    bits = entropy_bits(password)
    score = 0 if bits < 28 else 1 if bits < 40 else 2 if bits < 60 else 3 if bits < 80 else 4
    if "is a very common password" in problems:
        score = 0
    elif problems:
        score = min(score, 3)
    return score, problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check how strong a password is.")
    parser.add_argument("password", nargs="?", help="password to check (default: prompt or stdin)")
    args = parser.parse_args(argv)

    password = args.password
    if password is None:
        if sys.stdin.isatty():
            password = getpass.getpass("Password: ")
        else:
            password = sys.stdin.readline().rstrip("\n")
    if not password:
        print("No password given.", file=sys.stderr)
        return 2
    score, problems = analyze(password)
    print(f"Strength: {LABELS[score]} ({score}/4), about {entropy_bits(password):.0f} bits")
    print(f"Length:   {len(password)} characters")
    for problem in problems:
        print(f"- It {problem}.")
    if not problems:
        print("No obvious weaknesses found.")
    return 0 if score >= 3 else 1


if __name__ == "__main__":
    sys.exit(main())
