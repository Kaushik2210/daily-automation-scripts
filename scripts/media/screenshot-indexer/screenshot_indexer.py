"""Index screenshots with the text found in them (OCR) so you can search them later."""
import argparse
import json
import re
import shutil
import subprocess  # web-ok: tesseract only runs when installed; sidecar .txt files work anywhere
import sys
from pathlib import Path

from PIL import Image

EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
DATE = re.compile(r"(20\d{2})[-_.]?(\d{2})[-_.]?(\d{2})")


def ocr_text(path):
    """Return (text, source): a sidecar .txt file first, then the tesseract program."""
    for sidecar in (path.with_name(path.name + ".txt"), path.with_suffix(".txt")):
        if sidecar.is_file():
            return sidecar.read_text(encoding="utf-8", errors="replace").strip(), "sidecar"
    exe = shutil.which("tesseract")
    if exe:
        result = subprocess.run([exe, str(path), "stdout"], capture_output=True, text=True,
                                timeout=120, check=False)
        if result.returncode == 0:
            return result.stdout.strip(), "tesseract"
    return "", "none"


def describe(path, old=None):
    """Index entry for one image, reusing the old one when the file is unchanged."""
    stat = path.stat()
    if old and old.get("size") == stat.st_size and old.get("mtime") == round(stat.st_mtime):
        return old, False
    with Image.open(path) as img:
        width, height = img.size
    text, source = ocr_text(path)
    match = DATE.search(path.name)
    return {"size": stat.st_size, "mtime": round(stat.st_mtime), "width": width,
            "height": height, "text": " ".join(text.split()), "ocr": source,
            "date": "-".join(match.groups()) if match else ""}, True


def snippet(text, terms, width=60):
    lowered = text.lower()
    positions = [lowered.find(t) for t in terms if t in lowered]
    start = max(0, min(positions) - 20) if positions else 0
    piece = text[start:start + width]
    return ("..." if start else "") + piece + ("..." if start + width < len(text) else "")


def search(index, query):
    terms = query.lower().split()
    hits = []
    for name, entry in sorted(index.get("images", {}).items()):
        haystack = f"{name} {entry.get('text', '')}".lower()
        if all(term in haystack for term in terms):
            hits.append((name, entry))
    return hits, terms


def load_index(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data.get("images"), dict) else {"images": {}}
    except (OSError, ValueError, AttributeError):
        return {"images": {}}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Index and search screenshots by their text.")
    parser.add_argument("action", choices=["index", "search"])
    parser.add_argument("value", help="the folder to index, or the words to search for")
    parser.add_argument("--index", type=Path, default=Path("screenshots-index.json"),
                        help="index file (screenshots-index.json)")
    parser.add_argument("--apply", action="store_true",
                        help="really write the index file (default is a dry run)")
    args = parser.parse_args(argv)

    index = load_index(args.index)
    if args.action == "search":
        if not index["images"]:
            print(f"No index at {args.index}. Run 'index FOLDER --apply' first.", file=sys.stderr)
            return 1
        hits, terms = search(index, args.value)
        for name, entry in hits:
            print(f"{name}  ({entry['width']}x{entry['height']}"
                  + (f", {entry['date']}" if entry.get("date") else "") + ")")
            if entry.get("text"):
                print(f"    {snippet(entry['text'], terms)}")
        print(f"\n{len(hits)} match(es) in {len(index['images'])} indexed image(s).")
        return 0 if hits else 1

    folder = Path(args.value)
    if not folder.is_dir():
        parser.error(f"not a folder: {folder}")
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in EXTENSIONS)
    new = updated = unchanged = failed = 0
    for path in files:
        key = path.name
        try:
            entry, changed = describe(path, index["images"].get(key))
        except OSError as err:
            print(f"skip {key}: not an image I can read ({err})")
            failed += 1
            continue
        if not changed:
            unchanged += 1
            continue
        new, updated = (new + 1, updated) if key not in index["images"] else (new, updated + 1)
        index["images"][key] = entry
        words = len(entry["text"].split())
        print(f"{key}: {entry['width']}x{entry['height']}, {words} word(s) of text "
              f"[{entry['ocr']}]" + (f"  {snippet(entry['text'], [], 40)}" if words else ""))
    missing = [n for n in index["images"] if not (folder / n).exists()]
    summary = f"{new} new, {updated} updated, {unchanged} unchanged"
    if missing:
        summary += f", {len(missing)} no longer in the folder (kept)"
    print(f"\n{len(files)} image(s): {summary}.")
    if not any(e["ocr"] != "none" for e in index["images"].values()) and files:
        print("No text was found. Put OCR text next to each image (shot.png.txt) or install "
              "Tesseract.")
    if not args.apply:
        print(f"Dry run. Use --apply to write {args.index}.")
        return 0
    args.index.write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    print(f"Saved {args.index}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
