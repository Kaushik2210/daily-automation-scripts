"""Convert between JSON and YAML files."""
import argparse
import json
import sys
from pathlib import Path

import yaml


def detect_format(path):
    return "yaml" if path.suffix.lower() in (".yaml", ".yml") else "json"


def convert(text, source, target):
    """Convert `text` from `source` format to `target` ('json' or 'yaml')."""
    data = yaml.safe_load(text) if source == "yaml" else json.loads(text)
    if target == "json":
        return json.dumps(data, indent=2, ensure_ascii=False)
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Convert JSON to YAML or YAML to JSON.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--to", choices=["json", "yaml"],
                        help="target format (default: the opposite of the input)")
    parser.add_argument("-o", "--output", type=Path, help="write the result to this file")
    parser.add_argument("--apply", action="store_true",
                        help="really write --output (default only prints the result)")
    args = parser.parse_args(argv)
    if not args.file.is_file():
        parser.error(f"not a file: {args.file}")

    source = detect_format(args.file)
    target = args.to or ("yaml" if source == "json" else "json")
    try:
        result = convert(args.file.read_text(encoding="utf-8-sig"), source, target)
    except (json.JSONDecodeError, yaml.YAMLError) as err:
        print(f"Couldn't read {args.file} as {source}: {err}", file=sys.stderr)
        return 1
    if args.output and args.apply:
        args.output.write_text(result, encoding="utf-8")
        print(f"Wrote {args.output} ({target}).")
    else:
        print(result.rstrip("\n"))
        if args.output:
            print(f"(preview only: use --apply to write {args.output})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
