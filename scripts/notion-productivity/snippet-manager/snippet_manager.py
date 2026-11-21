"""Store text snippets (email replies, code, addresses) and paste them via the clipboard."""
import argparse
import json
import platform
import shutil
import subprocess  # web-ok: only `copy` talks to the clipboard; the other actions work anywhere
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_STORE = Path.home() / "snippets.json"
WRITERS = {"Darwin": [["pbcopy"]],
           "Linux": [["wl-copy"], ["xclip", "-selection", "clipboard"],
                     ["xsel", "--clipboard", "--input"]]}


def load(store):
    if not store.exists():
        return {}
    data = json.loads(store.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("the snippet file must hold a JSON object")
    return data


def save(store, snippets):
    store.write_text(json.dumps(dict(sorted(snippets.items())), indent=1, ensure_ascii=False)
                     + "\n", encoding="utf-8")


def fill(text, now=None):
    """Replace {date}, {time} and {datetime} placeholders."""
    now = now or datetime.now()
    return (text.replace("{datetime}", f"{now:%Y-%m-%d %H:%M}").replace("{date}", f"{now:%Y-%m-%d}")
            .replace("{time}", f"{now:%H:%M}"))


def set_clipboard(text):
    """Put text on the clipboard; raise OSError when no clipboard tool exists."""
    if platform.system() == "Windows":
        if not shutil.which("clip"):
            raise OSError("no clipboard tool found")
        subprocess.run(["clip"], input=b"\xff\xfe" + text.encode("utf-16-le"), timeout=10,
                       check=True)
        return
    for command in WRITERS.get(platform.system(), []):
        if shutil.which(command[0]):
            subprocess.run(command, input=text.encode("utf-8"), timeout=10, check=True)
            return
    raise OSError("no clipboard tool found (need pbcopy, wl-copy, xclip or xsel)")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Keep and paste text snippets.")
    parser.add_argument("action", choices=["add", "list", "show", "copy", "search", "delete"])
    parser.add_argument("name", nargs="?", help="snippet name (or search word)")
    parser.add_argument("text", nargs="?", help="the text to save (add)")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE,
                        help=f"snippet file ({DEFAULT_STORE.name} in your home folder)")
    parser.add_argument("--file", type=Path, help="read the text for add from this file")
    parser.add_argument("--overwrite", action="store_true", help="replace an existing snippet")
    parser.add_argument("--apply", action="store_true", help="really delete (default is a dry run)")
    args = parser.parse_args(argv)
    try:
        snippets = load(args.store)
    except (OSError, ValueError) as err:
        print(f"Can't read {args.store}: {err}", file=sys.stderr)
        return 1

    if args.action == "list":
        for name, item in sorted(snippets.items()):
            print(f"{name:<18} {len(item['text']):>5} chars  used {item.get('uses', 0)}x  "
                  f"{' '.join(item['text'].split())[:50]}")
        print(f"\n{len(snippets)} snippet(s) in {args.store.name}.")
        return 0
    if not args.name:
        parser.error(f"{args.action} needs a name")

    if args.action == "add":
        text = args.file.read_text(encoding="utf-8") if args.file else args.text
        if text is None:
            parser.error("add needs the text, or --file FILE")
        if args.name in snippets and not args.overwrite:
            print(f"'{args.name}' already exists; use --overwrite to replace it.", file=sys.stderr)
            return 1
        snippets[args.name] = {"text": text.rstrip("\n"), "created": datetime.now().strftime(
            "%Y-%m-%d"), "uses": snippets.get(args.name, {}).get("uses", 0)}
        save(args.store, snippets)
        print(f"Saved '{args.name}' ({len(text)} chars) in {args.store}.")
        return 0
    if args.action == "search":
        needle = args.name.lower()
        hits = [n for n, i in sorted(snippets.items()) if needle in n.lower()
                or needle in i["text"].lower()]
        for name in hits:
            print(f"{name:<18} {' '.join(snippets[name]['text'].split())[:60]}")
        print(f"\n{len(hits)} match(es).")
        return 0 if hits else 1

    if args.name not in snippets:
        close = [n for n in snippets if args.name.lower() in n.lower()]
        print(f"No snippet called '{args.name}'." + (f" Did you mean: {', '.join(close)}?"
                                                      if close else ""), file=sys.stderr)
        return 1
    if args.action == "delete":
        if not args.apply:
            print(f"Would delete '{args.name}'. Use --apply to do it.")
            return 0
        del snippets[args.name]
        save(args.store, snippets)
        print(f"Deleted '{args.name}'.")
        return 0

    text = fill(snippets[args.name]["text"])
    if args.action == "show":
        print(text)
        return 0
    try:
        set_clipboard(text)
    except (OSError, subprocess.SubprocessError) as err:
        print(f"Couldn't use the clipboard ({err}); here is the text instead:\n", file=sys.stderr)
        print(text)
        return 1
    snippets[args.name]["uses"] = snippets[args.name].get("uses", 0) + 1
    save(args.store, snippets)
    print(f"Copied '{args.name}' ({len(text)} chars) to the clipboard.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
