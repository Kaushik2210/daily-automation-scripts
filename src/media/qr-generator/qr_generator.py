"""Generate QR codes from text or URLs: print them in the terminal or save SVG/PNG files."""
import argparse
import sys
from pathlib import Path

import qrcode
from qrcode.constants import ERROR_CORRECT_H, ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q
from qrcode.image.svg import SvgPathImage

LEVELS = {"L": ERROR_CORRECT_L, "M": ERROR_CORRECT_M, "Q": ERROR_CORRECT_Q, "H": ERROR_CORRECT_H}


def build(text, level="M", border=2):
    qr = qrcode.QRCode(error_correction=LEVELS[level], border=border)
    qr.add_data(text)
    qr.make(fit=True)
    return qr


def to_text(matrix, ascii_only=False):
    """Draw the QR matrix with block characters (two matrix rows per text line)."""
    if ascii_only:
        return "\n".join("".join("##" if cell else "  " for cell in row) for row in matrix)
    blocks = {(False, False): " ", (True, False): "▀", (False, True): "▄",
              (True, True): "█"}
    lines = []
    for top, bottom in zip(matrix[::2], matrix[1::2] + [[False] * len(matrix[0])], strict=False):
        lines.append("".join(blocks[(t, b)] for t, b in zip(top, bottom, strict=True)))
    return "\n".join(lines)


def save(qr, path):
    """Write an SVG or PNG file depending on the extension."""
    if path.suffix.lower() == ".svg":
        qr.make_image(image_factory=SvgPathImage).save(str(path))
    else:
        qr.make_image().save(str(path))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate a QR code.")
    parser.add_argument("text", help="text or URL to encode")
    parser.add_argument("--level", choices=sorted(LEVELS), default="M",
                        help="error correction: L 7%%, M 15%%, Q 25%%, H 30%% (default M)")
    parser.add_argument("--ascii", action="store_true", help="draw with ## instead of blocks")
    parser.add_argument("-o", "--output", type=Path, help="save to this .svg or .png file")
    parser.add_argument("--apply", action="store_true",
                        help="really write --output (default only prints the code)")
    args = parser.parse_args(argv)

    qr = build(args.text, args.level)
    ascii_only = args.ascii
    try:
        "█".encode(sys.stdout.encoding or "utf-8")
    except UnicodeEncodeError:
        ascii_only = True
    print(to_text(qr.get_matrix(), ascii_only))
    print(f"\nQR version {qr.version}, {len(qr.get_matrix())} modules wide, level {args.level}.")
    if args.output:
        if args.apply:
            save(qr, args.output)
            print(f"Wrote {args.output}.")
        else:
            print(f"(preview only: use --apply to write {args.output})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
