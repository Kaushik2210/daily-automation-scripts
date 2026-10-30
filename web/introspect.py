"""Load a script and print its argparse options as JSON (used by the web interface).

The script is imported and its main() is called with parse_args patched, so the
parser is captured without running the tool itself.
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path


class Captured(Exception):
    def __init__(self, parser):
        super().__init__("parser captured")
        self.parser = parser


def load_parser(path):
    path = Path(path).resolve()
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def grab(self, args=None, namespace=None):
        raise Captured(self)

    original = argparse.ArgumentParser.parse_args
    argparse.ArgumentParser.parse_args = grab
    try:
        module.main([])
    except Captured as caught:
        return caught.parser
    finally:
        argparse.ArgumentParser.parse_args = original
    raise RuntimeError("this script does not build an argparse parser")


def jsonable(value):
    try:
        json.dumps(value)
    except TypeError:
        return str(value)
    return value


def describe(parser):
    arguments = []
    for action in parser._actions:
        if isinstance(action, argparse._HelpAction):
            continue
        if isinstance(action, argparse._StoreTrueAction | argparse._StoreFalseAction):
            kind = "flag"
        elif isinstance(action, argparse._AppendAction) or action.nargs in ("*", "+"):
            kind = "multi"
        else:
            kind = "value"
        default = None if action.default is argparse.SUPPRESS else jsonable(action.default)
        arguments.append({
            "dest": action.dest,
            "flags": list(action.option_strings),
            "positional": not action.option_strings,
            "kind": kind,
            "type": getattr(action.type, "__name__", "str") if action.type else "str",
            "help": action.help or "",
            "choices": [jsonable(c) for c in action.choices] if action.choices else None,
            "default": default,
            "required": bool(action.required),
            "metavar": action.metavar if isinstance(action.metavar, str) else None,
            "nargs": action.nargs if isinstance(action.nargs, str) else None,
        })
    return {"description": parser.description or "", "arguments": arguments}


def schema_for(path):
    """Return the options of a script, or {'error': ...} if it can't be loaded."""
    try:
        return describe(load_parser(path))
    except Exception as err:  # report any import or setup problem instead of crashing
        return {"error": f"{type(err).__name__}: {err}"}


def main():
    print(json.dumps(schema_for(sys.argv[1])))


if __name__ == "__main__":
    main()
