"""Run every tool's built-in example in a scratch folder and report which ones work.

Usage: python web/run_examples.py [--only NAME] [--verbose]
"""
import argparse
import base64
import json
import sys
import tempfile
from pathlib import Path

from dashboard import ROOT, build_argv, discover, get_schema, run_script

HERE = Path(__file__).resolve().parent


def load_json(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def materialize(folder, samples):
    """Write the sample files (text, base64 binary or empty folders) into `folder`."""
    folder = Path(folder)
    for name, content in samples.items():
        target = folder / name
        if name.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, dict):
            target.write_bytes(base64.b64decode(content["base64"]))
        else:
            target.write_bytes(content.encode("utf-8"))


def run_example(info, example, samples):
    """Run one tool's example in a fresh workspace. Returns a dict with 'ok' and 'detail'."""
    with tempfile.TemporaryDirectory() as scratch:
        materialize(scratch, samples)
        schema = get_schema(info["path"])
        if "error" in schema:
            return {"ok": False, "detail": f"couldn't read options: {schema['error']}", "out": ""}
        try:
            argv = build_argv(schema["arguments"], example["values"])
        except ValueError as err:
            return {"ok": False, "detail": f"bad example values: {err}", "out": ""}
        result = run_script(info["path"], argv, timeout=60, cwd=scratch)
    out = result["stdout"].strip()
    if result["timed_out"]:
        return {"ok": False, "detail": "timed out", "out": out}
    if result["exit_code"] not in example.get("exit", [0]):
        err = (result["stderr"].strip().splitlines() or ["no error text"])[-1]
        return {"ok": False, "detail": f"exit {result['exit_code']}: {err}", "out": out}
    if not out:
        return {"ok": False, "detail": "ran but printed nothing", "out": out}
    return {"ok": True, "detail": "ok", "out": out}


def run_all(only=None, root=ROOT):
    """Return {tool_id: result} for every discovered tool."""
    samples, examples = load_json("samples.json"), load_json("examples.json")
    results = {}
    for tool_id, info in discover(root).items():
        if only and only not in tool_id:
            continue
        example = examples.get(tool_id)
        if example is None:
            results[tool_id] = {"ok": False, "detail": "no example in web/examples.json", "out": ""}
        else:
            results[tool_id] = run_example(info, example, samples)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run every tool's example and report results.")
    parser.add_argument("--only", help="only tools whose id contains this text")
    parser.add_argument("-v", "--verbose", action="store_true", help="show each tool's output")
    args = parser.parse_args(argv)

    results = run_all(args.only)
    for tool_id, result in results.items():
        note = "" if result["ok"] else result["detail"]
        print(f"{'PASS' if result['ok'] else 'FAIL'}  {tool_id}  {note}")
        if args.verbose and result["out"]:
            print("      " + result["out"].replace("\n", "\n      ")[:600])
    failed = [t for t, r in results.items() if not r["ok"]]
    print(f"\n{len(results) - len(failed)}/{len(results)} tools produced results.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
