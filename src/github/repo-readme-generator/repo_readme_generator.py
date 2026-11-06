"""Draft a README for a project by looking at the files it contains."""
import argparse
import json
import sys
from pathlib import Path

SKIP = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".idea"}
LANGUAGES = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".go": "Go",
             ".rs": "Rust", ".java": "Java", ".rb": "Ruby", ".cs": "C#", ".php": "PHP"}


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def detect(folder):
    """Gather facts about the project folder into a dict."""
    folder = Path(folder)
    package = read_json(folder / "package.json")
    counts = {}
    for path in folder.rglob("*"):
        if path.is_file() and not any(part in SKIP for part in path.relative_to(folder).parts):
            language = LANGUAGES.get(path.suffix.lower())
            if language:
                counts[language] = counts.get(language, 0) + 1
    license_line = ""
    for name in ("LICENSE", "LICENSE.md", "LICENSE.txt"):
        if (folder / name).is_file():
            license_line = (folder / name).read_text(encoding="utf-8").splitlines()[0].strip()
            break
    return {
        "name": package.get("name") or folder.resolve().name,
        "description": package.get("description", ""),
        "scripts": package.get("scripts", {}),
        "languages": sorted(counts, key=lambda lang: -counts[lang]),
        "has_package_json": bool(package),
        "has_requirements": (folder / "requirements.txt").is_file(),
        "has_pyproject": (folder / "pyproject.toml").is_file(),
        "license": package.get("license") or license_line,
        "tree": tree_lines(folder),
    }


def tree_lines(folder, depth=2):
    lines = []

    def walk(path, indent, level):
        visible = [p for p in path.iterdir() if p.name not in SKIP and not p.name.startswith(".")]
        entries = sorted(visible, key=lambda p: (not p.is_dir(), p.name.lower()))
        for entry in entries:
            lines.append(f"{'  ' * indent}{entry.name}{'/' if entry.is_dir() else ''}")
            if entry.is_dir() and level < depth:
                walk(entry, indent + 1, level + 1)

    walk(Path(folder), 0, 1)
    return lines


def render(info):
    blurb = info["description"] or "_A short description of what this project does._"
    out = [f"# {info['name']}", "", blurb, ""]
    if info["languages"]:
        out += [f"Built with {', '.join(info['languages'][:3])}.", ""]
    out += ["## Getting started", "", "```bash"]
    if info["has_package_json"]:
        out.append("npm install")
        out += [f"npm run {name}" if name != "start" else "npm start" for name in info["scripts"]]
    elif info["has_requirements"]:
        out.append("pip install -r requirements.txt")
    elif info["has_pyproject"]:
        out.append("pip install .")
    else:
        out.append("# add install and run commands here")
    out += ["```", "", "## Project structure", "", "```", *info["tree"], "```", ""]
    if info["license"]:
        out += ["## License", "", f"{info['license']}.", ""]
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Draft a README from a project folder.")
    parser.add_argument("folder", type=Path, nargs="?", default=Path("."))
    parser.add_argument("-o", "--output", type=Path, help="write the README to this file")
    parser.add_argument("--apply", action="store_true",
                        help="really write --output (default only prints the draft)")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")

    text = render(detect(args.folder))
    if args.output and args.apply:
        if args.output.exists():
            print(f"{args.output} already exists; it won't be overwritten.", file=sys.stderr)
            return 1
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}.")
        return 0
    print(text)
    if args.output:
        print(f"(preview only: use --apply to write {args.output})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
