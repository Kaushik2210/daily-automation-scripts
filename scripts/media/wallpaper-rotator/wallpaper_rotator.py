"""Rotate the desktop wallpaper through the pictures in a folder."""
import argparse
import json
import platform
import random
import shutil
import subprocess  # web-ok: only used with --apply to set the wallpaper; the dry run works anywhere
import sys
from datetime import date
from pathlib import Path

EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}
DEFAULT_STATE = Path.home() / ".wallpaper-rotator.json"


def pictures(folder):
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS)


def choose(files, mode, last=None, today=None, rng=None):
    """Pick the next picture. last is the name used before (or None)."""
    if mode == "daily":
        return files[(today or date.today()).toordinal() % len(files)]
    if mode == "random":
        options = [f for f in files if f.name != last] or files
        return (rng or random).choice(options)
    names = [f.name for f in files]
    return files[(names.index(last) + 1) % len(files)] if last in names else files[0]


def command_for(picture):
    """Return a description of how the wallpaper will be set on this system."""
    system = platform.system()
    if system == "Windows":
        return ["SystemParametersInfoW", "SPI_SETDESKWALLPAPER", str(picture)]
    if system == "Darwin":
        script = ('tell application "System Events" to tell every desktop to set picture to '
                  f'POSIX file "{picture}"')
        return ["osascript", "-e", script]
    if shutil.which("gsettings"):
        uri = picture.as_uri()
        return ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri]
    if shutil.which("feh"):
        return ["feh", "--bg-fill", str(picture)]
    raise OSError("no way to set the wallpaper found (need GNOME's gsettings or feh)")


def set_wallpaper(picture):
    command = command_for(picture)
    if command[0] == "SystemParametersInfoW":
        import ctypes
        ok = ctypes.windll.user32.SystemParametersInfoW(20, 0, str(picture), 3)
        if not ok:
            raise OSError("Windows refused to change the wallpaper")
        return
    subprocess.run(command, check=True, timeout=20)
    if command[0] == "gsettings":  # GNOME has a separate picture for dark mode
        subprocess.run([*command[:-2], "picture-uri-dark", picture.as_uri()], check=False,
                       timeout=20)


def load_state(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Change the wallpaper from a folder of pictures.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--mode", choices=["next", "random", "daily"], default="next",
                        help="next: in order, random, daily: one per day (next)")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE,
                        help=f"remembers the last picture ({DEFAULT_STATE.name} in your home)")
    parser.add_argument("--seed", type=int, help="make random choices repeatable")
    parser.add_argument("--apply", action="store_true",
                        help="really change the wallpaper (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")
    files = pictures(args.folder)
    if not files:
        print("No pictures (png, jpg, bmp) found in that folder.", file=sys.stderr)
        return 1

    state = load_state(args.state)
    last = state.get(str(args.folder.resolve()))
    picture = choose(files, args.mode, last, rng=random.Random(args.seed) if args.seed is not None
                     else None).resolve()
    print(f"{len(files)} picture(s) in {args.folder}; mode {args.mode}.")
    print(f"Next wallpaper: {picture.name}" + (f"  (after {last})" if last else ""))
    try:
        command = command_for(picture)
    except OSError as err:
        if args.apply:
            print(f"Can't set the wallpaper here: {err}", file=sys.stderr)
            return 1
        print(f"(This system can't set the wallpaper: {err})\nDry run only.")
        return 0
    if not args.apply:
        print(f"Would run: {' '.join(command[:2])} ...\nDry run. Use --apply to change it.")
        return 0
    try:
        set_wallpaper(picture)
    except (OSError, subprocess.SubprocessError) as err:
        print(f"Couldn't set the wallpaper: {err}", file=sys.stderr)
        return 1
    state[str(args.folder.resolve())] = picture.name
    args.state.write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8")
    print("Wallpaper changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
