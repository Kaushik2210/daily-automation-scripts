# import-graph-builder

## Purpose
See how the modules of a Python project depend on each other. The tool reads every `.py` file (without running any code), resolves `import x`, `from x import y` and relative imports like `from . import sibling`, and builds the graph of which module imports which. The report shows each module's imports and importers, the most-imported modules, isolated modules, the third-party packages the project needs, and **import cycles** (modules that import each other in a loop, a common cause of "partially initialised module" errors).

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python import_graph_builder.py PROJECT_FOLDER [--dot imports.dot] [--json imports.json] [--fail-on-cycles]
```
The folder is the import root: `pkg/sub/mod.py` becomes the module `pkg.sub.mod`. `__pycache__`, virtual environments and `node_modules` are skipped. `--dot` writes a Graphviz file (modules in a cycle are drawn in red) and `--json` the full data; both create new files and refuse to overwrite existing ones. The exit code is 1 when a file can't be parsed, or when cycles exist and you passed `--fail-on-cycles`, so it can guard a CI pipeline.

## Example
```bash
python import_graph_builder.py pyproj/
```
```
7 module(s), 6 internal import(s)

MODULE                 IMPORTS IMPORTED BY  external packages
app                          0           0  -
app.core                     2           3  -
app.legacy                   0           0  -
app.main                     2           0  requests
app.models                   0           1  -
app.utils                    1           2  -
tests.test_core              1           0  -

Most imported: app.core (3), app.utils (2), app.models (1)
Isolated (no imports in or out): app, app.legacy
Third-party packages used: requests
CYCLE: app.core <-> app.utils
```

## Notes
- Imports inside functions and `if TYPE_CHECKING:` blocks count too, and standard-library modules are not listed as third-party.
- Dynamic imports (`importlib.import_module(name)`) can't be seen.
- Render the graph with `dot -Tpng imports.dot -o imports.png` after installing Graphviz.
- Use `dead-code-finder` to find functions nobody calls.
