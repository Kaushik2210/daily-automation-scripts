"""Map the imports between the Python modules of a project, and find import cycles."""
import argparse
import ast
import json
import sys
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "build", "dist", ".tox",
             ".mypy_cache", ".pytest_cache", "site-packages"}


def module_name(root, path):
    """pkg/sub/mod.py -> 'pkg.sub.mod' ; pkg/__init__.py -> 'pkg'."""
    parts = list(path.relative_to(root).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def find_modules(root):
    """Return {module name: path} for every .py file under the root."""
    modules = {}
    for path in sorted(root.rglob("*.py")):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts[:-1]):
            continue
        name = module_name(root, path)
        if name:
            modules[name] = path
    return modules


def raw_imports(tree, current, is_package):
    """Yield (absolute module name, imported names) for every import statement in the tree."""
    package = current if is_package else current.rpartition(".")[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, []
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = package.split(".") if package else []
                parts = parts[:len(parts) - node.level + 1] if node.level > 1 else parts
                base = ".".join([*parts, *([base] if base else [])])
            yield base, [alias.name for alias in node.names]


def resolve(name, names, modules):
    """The internal modules an import refers to ('from app import core' -> app.core)."""
    found = {f"{name}.{n}" for n in names if f"{name}.{n}" in modules}
    plain = [n for n in names if f"{name}.{n}" not in modules]  # functions, classes, constants
    if name in modules and (plain or not names):
        found.add(name)
    if not found:  # 'import app.sub.thing' (or an import of something not a module): closest module
        prefix = name
        while prefix and prefix not in modules:
            prefix = prefix.rpartition(".")[0]
        if prefix:
            found.add(prefix)
    return found


def build_graph(root):
    """Return (internal graph {module: set}, external {module: set of top-level packages},
    problems list)."""
    modules = find_modules(root)
    graph, external, problems = {}, {}, []
    for name, path in modules.items():
        graph[name], external[name] = set(), set()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as err:
            problems.append(f"{path.relative_to(root).as_posix()}: can't parse ({err.msg})")
            continue
        for target, names in raw_imports(tree, name, path.name == "__init__.py"):
            internal = resolve(target, names, modules) if target else set()
            internal.discard(name)
            if internal:
                graph[name] |= internal
            elif target:
                external[name].add(target.split(".")[0])
    return graph, external, problems


def find_cycles(graph):
    """Strongly connected components with more than one module (Tarjan's algorithm)."""
    index, stack, on_stack, lows, order, cycles = {}, [], set(), {}, [0], []

    def visit(node):
        index[node] = lows[node] = order[0]
        order[0] += 1
        stack.append(node)
        on_stack.add(node)
        for target in sorted(graph.get(node, ())):
            if target not in index:
                visit(target)
                lows[node] = min(lows[node], lows[target])
            elif target in on_stack:
                lows[node] = min(lows[node], index[target])
        if lows[node] == index[node]:
            component = []
            while True:
                member = stack.pop()
                on_stack.discard(member)
                component.append(member)
                if member == node:
                    break
            if len(component) > 1:
                cycles.append(sorted(component))

    sys.setrecursionlimit(max(sys.getrecursionlimit(), 5 * len(graph) + 100))
    for node in sorted(graph):
        if node not in index:
            visit(node)
    return sorted(cycles)


def to_dot(graph, cycles):
    in_cycle = {m for c in cycles for m in c}
    lines = ["digraph imports {", "  rankdir=LR;", "  node [shape=box, fontsize=10];"]
    for module in sorted(graph):
        style = ", color=red" if module in in_cycle else ""
        lines.append(f'  "{module}" [label="{module}"{style}];')
        lines += [f'  "{module}" -> "{t}";' for t in sorted(graph[module])]
    return "\n".join(lines + ["}"]) + "\n"


def write_new(path, text):
    if path.exists():
        raise FileExistsError(f"{path} already exists; choose another name")
    path.write_text(text, encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Map imports between Python modules.")
    parser.add_argument("folder", type=Path, help="the project's import root")
    parser.add_argument("--dot", type=Path, help="write a Graphviz .dot file (new file)")
    parser.add_argument("--json", type=Path, help="write the graph as JSON (new file)")
    parser.add_argument("--fail-on-cycles", action="store_true", help="exit with 1 if cycles exist")
    args = parser.parse_args(argv)
    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")

    graph, external, problems = build_graph(args.folder)
    if not graph:
        print("No Python files found.", file=sys.stderr)
        return 1
    imported_by = {m: sorted(o for o, t in graph.items() if m in t) for m in graph}
    stdlib = set(sys.stdlib_module_names)
    third_party = sorted({p for pkgs in external.values() for p in pkgs if p not in stdlib})
    print(f"{len(graph)} module(s), {sum(len(t) for t in graph.values())} internal import(s)\n")
    print(f"{'MODULE':<22} {'IMPORTS':>7} {'IMPORTED BY':>11}  external packages")
    for module in sorted(graph):
        outside = ", ".join(sorted(external[module] - stdlib)) or "-"
        print(f"{module:<22} {len(graph[module]):>7} {len(imported_by[module]):>11}  {outside}")
    top = sorted(graph, key=lambda m: (-len(imported_by[m]), m))[:3]
    popular = ", ".join(f"{m} ({len(imported_by[m])})" for m in top if imported_by[m])
    print(f"\nMost imported: {popular or '-'}")
    unused = [m for m in sorted(graph) if not imported_by[m] and not graph[m]]
    if unused:
        print("Isolated (no imports in or out): " + ", ".join(unused))
    print("Third-party packages used: " + (", ".join(third_party) or "none"))
    cycles = find_cycles(graph)
    for cycle in cycles:
        print("CYCLE: " + " <-> ".join(cycle))
    if not cycles:
        print("No import cycles.")
    for problem in problems:
        print(f"PROBLEM  {problem}")
    try:
        if args.dot:
            write_new(args.dot, to_dot(graph, cycles))
        if args.json:
            data = {"modules": {m: {"imports": sorted(graph[m]), "imported_by": imported_by[m],
                                    "external": sorted(external[m])} for m in sorted(graph)},
                    "cycles": cycles}
            write_new(args.json, json.dumps(data, indent=1) + "\n")
    except FileExistsError as err:
        print(err, file=sys.stderr)
        return 1
    return 1 if (cycles and args.fail_on_cycles) or problems else 0


if __name__ == "__main__":
    sys.exit(main())
