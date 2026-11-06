"""Generate strong random passwords and passphrases using the secrets module."""
import argparse
import math
import secrets
import string
import sys

WORDS = [
    "able", "acid", "aged", "also", "area", "army", "away", "baby", "back", "ball", "band",
    "bank", "base", "bath", "bear", "beat", "bell", "belt", "bend", "bike", "bird", "blue",
    "boat", "body", "bold", "bone", "book", "boot", "born", "boss", "bowl", "bulb", "bush",
    "busy", "cafe", "cake", "calm", "camp", "card", "care", "cart", "cash", "cave", "chip",
    "city", "clay", "clip", "club", "coal", "coat", "code", "coin", "cold", "cook", "cool",
    "corn", "cost", "crew", "crop", "dark", "dawn", "deal", "deep", "deer", "desk", "dial",
    "dish", "dive", "door", "dove", "down", "draw", "drum", "duck", "dust", "east", "easy",
    "edge", "face", "fair", "farm", "fast", "fern", "film", "fire", "fish", "flag", "flat",
    "flow", "foam", "fold", "food", "fork", "frog", "fuel", "game", "gate", "gift", "glad",
    "glow", "goat", "gold", "golf", "good", "grid", "grip", "hall", "hand", "harp", "hawk",
    "heat", "herb", "hill", "hint", "hold", "home", "hope", "horn", "iron", "isle", "jade",
    "jazz", "join", "jump", "keen", "kind", "king", "kite", "lake", "lamp", "land", "lark",
    "leaf", "lime", "lion", "loop", "lost", "maple", "moon", "moss", "navy", "nest", "note",
    "oak", "oat", "open", "oval", "pace", "palm", "park", "path", "peak", "pine", "plum",
    "pond", "pool", "rain", "reed", "ring", "rock", "roof", "rope", "sage", "sail", "salt",
    "sand", "seed", "ship", "silk", "snow", "soup", "star", "tide", "tree", "vale", "wave",
    "wind", "wolf", "wood", "yard", "zinc",
]
AMBIGUOUS = "O0oIl1|"
SYMBOLS = "!@#$%^&*()-_=+[]{};:,.?"


def make_password(length=16, symbols=True, avoid_ambiguous=False):
    """Random password that always contains each requested kind of character."""
    groups = [string.ascii_lowercase, string.ascii_uppercase, string.digits]
    if symbols:
        groups.append(SYMBOLS)
    if avoid_ambiguous:
        groups = ["".join(c for c in g if c not in AMBIGUOUS) for g in groups]
    if length < len(groups):
        raise ValueError(f"length must be at least {len(groups)}")
    alphabet = "".join(groups)
    chars = [secrets.choice(g) for g in groups]
    chars += [secrets.choice(alphabet) for _ in range(length - len(chars))]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def make_passphrase(words=5, separator="-", capitalize=False):
    picked = [secrets.choice(WORDS) for _ in range(words)]
    if capitalize:
        picked = [w.capitalize() for w in picked]
    return separator.join(picked)


def bits_of_entropy(count, pool):
    return count * math.log2(pool)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate random passwords or passphrases.")
    parser.add_argument("-n", "--count", type=int, default=1, help="how many to generate")
    parser.add_argument("-l", "--length", type=int, default=16, help="password length (16)")
    parser.add_argument("--no-symbols", action="store_true", help="letters and digits only")
    parser.add_argument("--no-ambiguous", action="store_true",
                        help="avoid look-alike characters such as O, 0, l and 1")
    parser.add_argument("--passphrase", type=int, metavar="WORDS",
                        help="make a passphrase of this many words instead")
    parser.add_argument("--separator", default="-", help="word separator for passphrases")
    args = parser.parse_args(argv)
    if args.count < 1:
        parser.error("--count must be at least 1")

    try:
        for _ in range(args.count):
            if args.passphrase:
                print(make_passphrase(args.passphrase, args.separator, capitalize=True))
            else:
                print(make_password(args.length, not args.no_symbols, args.no_ambiguous))
    except ValueError as err:
        parser.error(str(err))
    if args.passphrase:
        bits = bits_of_entropy(args.passphrase, len(WORDS))
        print(f"~{bits:.0f} bits from a {len(WORDS)}-word list; use more words for more strength.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
