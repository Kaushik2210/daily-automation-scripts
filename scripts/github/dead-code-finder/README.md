# dead-code-finder

## Purpose
Spot functions, methods and classes that nothing in your project appears to use, so you can delete them with confidence or wire them up. The tool parses every Python file (without running it), collects the names of all definitions, then collects every name that is *mentioned* anywhere (calls, attribute access, imports, keyword arguments, and even strings, so `getattr(obj, "name")` and `__all__` lists keep things alive). A definition that is never mentioned is reported with its file and line. Code used only by the tests is listed separately.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python dead_code_finder.py PROJECT_FOLDER [--entry name1,name2] [--include-tests] [--fail-on-found]
```
Not judged: dunder methods (`__init__`...), `main` and similar entry points (`run`, `setup`, `handler`), `test_*` functions, and anything with a framework decorator (such as `@app.route` or `@pytest.fixture`), because those are called by something outside your code; the summary says how many were skipped. Add your own entry points with `--entry`. The exit code is 1 with `--fail-on-found` when unused code exists, which makes it a code-health gate.

## Example
```bash
python dead_code_finder.py pyproj/
```
```
app/core.py:11  unused function _unused_helper
app/core.py:22  unused method never_called
app/legacy.py:4  unused function legacy_import
app/legacy.py:8  unused function legacy_export
app/utils.py:11  unused function old_format
app/utils.py:15  unused function uses_core

Checked 11 definition(s): 6 look unused, 0 used only by tests; 0 decorated (framework-registered) definition(s) were not judged.
This is a name-based guess: check each hit before deleting it.
```

## Notes
- The check is **name-based**, not a full program analysis: two different functions called `render` count as one name, so some dead code will be missed, and code reached only by plugins, templates or reflection can look dead when it isn't. Review each hit.
- Common libraries like `vulture` do a deeper analysis; this tool is the dependency-free quick check.
- Use `import-graph-builder` to find whole modules that nothing imports.
