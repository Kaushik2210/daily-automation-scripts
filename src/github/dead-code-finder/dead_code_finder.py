"""Find functions, methods and classes in a Python project that nothing seems to use."""
import argparse
import ast
import sys
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "build", "dist", ".tox",
             ".mypy_cache", ".pytest_cache", "site-packages"}
PLAIN_DECORATORS = {"staticmethod", "classmethod", "property", "abstractmethod", "cached_property",
                    "overload", "final", "override", "setter", "getter", "deleter"}
DEFAULT_ENTRY = {"main", "run", "setup", "handler", "lambda_handler"}


def is_test_file(path):
    return ("tests" in path.parts or "test" in path.parts or path.name.startswith("test_")
            or path.name.endswith("_test.py") or path.name == "conftest.py")


def decorator_name(node):
    target = node.func if isinstance(node, ast.Call) else node
    if isinstance(target, ast.Attribute):
        return target.attr
    return target.id if isinstance(target, ast.Name) else ""


def definitions(tree):
    """Yield (name, kind, line, framework_decorated) for functions, methods and classes."""
    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if isinstance(parents.get(node), (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue  # nested helpers are used by their parent
            inside_class = isinstance(parents.get(node), ast.ClassDef)
            kind = "class" if isinstance(node, ast.ClassDef) else (
                "method" if inside_class else "function")
            framework = any(decorator_name(d) not in PLAIN_DECORATORS and decorator_name(d)
                            != "dataclass" for d in node.decorator_list)
            yield node.name, kind, node.lineno, framework


def references(tree):
    """Every name that is mentioned in the code: variables, attributes, imports, strings."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add(alias.name.split(".")[-1])
                if alias.asname:
                    names.add(alias.asname)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and (
                node.value.isidentifier() and len(node.value) < 60):
            names.add(node.value)  # getattr(obj, "name"), __all__, registries
        elif isinstance(node, ast.keyword) and node.arg:
            names.add(node.arg)
    return names


def analyse(root, entry=frozenset(), include_tests=False):
    """Return (unused, only_in_tests, counts) for the project."""
    defs, used_in_code, used_in_tests, skipped_files, framework = [], set(), set(), [], 0
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root)
        if any(part in SKIP_DIRS for part in relative.parts[:-1]):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            skipped_files.append(relative.as_posix())
            continue
        testing = is_test_file(relative)
        (used_in_tests if testing else used_in_code).update(references(tree))
        if testing and not include_tests:
            continue
        for name, kind, line, decorated in definitions(tree):
            if decorated:
                framework += 1
            elif not (name.startswith("__") and name.endswith("__")) and (
                    name not in DEFAULT_ENTRY and name not in entry and not name.startswith(
                        ("test_", "Test"))):
                defs.append((relative.as_posix(), line, kind, name))
    unused, only_tests = [], []
    for item in defs:
        name = item[3]
        if name in used_in_code:
            continue
        (only_tests if name in used_in_tests else unused).append(item)
    return unused, only_tests, {"checked": len(defs), "framework": framework,
                                "unparsed": skipped_files}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find unused functions in a Python project.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--entry", default="", help="extra names that are used from outside "
                                                     "(entry points), comma-separated")
    parser.add_argument("--include-tests", action="store_true",
                        help="also check the test files' own functions")
    parser.add_argument("--fail-on-found", action="store_true", help="exit with 1 if any are found")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")

    entry = {n.strip() for n in args.entry.split(",") if n.strip()}
    unused, only_tests, counts = analyse(args.folder, entry, args.include_tests)
    if not counts["checked"]:
        print("No Python definitions found.", file=sys.stderr)
        return 1
    for path, line, kind, name in sorted(unused):
        print(f"{path}:{line}  unused {kind} {name}")
    if only_tests:
        print("\nUsed only by tests (maybe dead code, maybe fine):")
        for path, line, kind, name in sorted(only_tests):
            print(f"{path}:{line}  {kind} {name}")
    for path in counts["unparsed"]:
        print(f"skipped {path}: syntax error")
    print(f"\nChecked {counts['checked']} definition(s): {len(unused)} look unused, "
          f"{len(only_tests)} used only by tests; {counts['framework']} decorated "
          "(framework-registered) definition(s) were not judged.")
    print("This is a name-based guess: check each hit before deleting it.")
    return 1 if unused and args.fail_on_found else 0


if __name__ == "__main__":
    sys.exit(main())
