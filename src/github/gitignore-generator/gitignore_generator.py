"""Generate a .gitignore for the languages, tools and operating systems you use."""
import argparse
import sys
from pathlib import Path

TEMPLATES = {
    "python": ["__pycache__/", "*.py[cod]", "*.egg-info/", ".venv/", "venv/", "build/", "dist/",
               ".pytest_cache/", ".mypy_cache/", ".ruff_cache/", ".coverage", "htmlcov/"],
    "node": ["node_modules/", "npm-debug.log*", "yarn-error.log", ".npm/", "dist/", "build/",
             "coverage/", ".next/", ".nuxt/", ".parcel-cache/"],
    "java": ["*.class", "*.jar", "*.war", "target/", ".gradle/", "build/", "out/", "hs_err_pid*"],
    "go": ["*.exe", "*.test", "*.out", "vendor/", "bin/"],
    "rust": ["target/", "**/*.rs.bk", "Cargo.lock"],
    "dotnet": ["bin/", "obj/", "*.user", "*.suo", ".vs/", "packages/"],
    "dotenv": [".env", ".env.*", "!.env.example"],
    "macos": [".DS_Store", ".AppleDouble", ".LSOverride", "._*"],
    "windows": ["Thumbs.db", "ehthumbs.db", "Desktop.ini", "$RECYCLE.BIN/"],
    "linux": ["*~", ".directory", ".Trash-*"],
    "vscode": [".vscode/*", "!.vscode/settings.json", "!.vscode/extensions.json"],
    "jetbrains": [".idea/", "*.iml", "*.iws", "out/"],
    "logs": ["*.log", "logs/", "*.tmp", "*.swp"],
}


def generate(stacks):
    """Return the .gitignore text for the chosen stacks (in the order given, no repeats)."""
    seen, blocks = set(), []
    for stack in stacks:
        lines = [line for line in TEMPLATES[stack] if line not in seen]
        seen.update(lines)
        if lines:
            blocks.append("\n".join([f"# {stack}", *lines]))
    return "\n\n".join(blocks) + "\n"


def missing_lines(existing, wanted):
    have = {line.strip() for line in existing.splitlines()}
    return [line for line in wanted.splitlines() if line.strip() and line.strip() not in have]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate a .gitignore.")
    parser.add_argument("stacks", nargs="+", choices=sorted(TEMPLATES), metavar="STACK",
                        help=f"one or more of: {', '.join(sorted(TEMPLATES))}")
    parser.add_argument("-o", "--output", type=Path, help="write to this file (e.g. .gitignore)")
    parser.add_argument("--append", action="store_true",
                        help="add only missing lines to an existing --output file")
    parser.add_argument("--apply", action="store_true",
                        help="really write --output (default only prints the result)")
    args = parser.parse_args(argv)

    text = generate(args.stacks)
    if not (args.output and args.apply):
        print(text, end="")
        if args.output:
            print(f"(preview only: use --apply to write {args.output})", file=sys.stderr)
        return 0
    if args.output.exists() and not args.append:
        print(f"{args.output} already exists. Use --append to add missing lines.", file=sys.stderr)
        return 1
    if args.output.exists():
        extra = [ln for ln in missing_lines(args.output.read_text(encoding="utf-8"), text)
                 if not ln.startswith("#")]
        with args.output.open("a", encoding="utf-8") as handle:
            handle.write("\n# added by gitignore-generator\n" + "\n".join(extra) + "\n")
        print(f"Appended {len(extra)} line(s) to {args.output}.")
    else:
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
