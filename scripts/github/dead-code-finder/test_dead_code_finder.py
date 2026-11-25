import ast

import dead_code_finder as dcf
import pytest


def project(tmp_path, files):
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return tmp_path


def names(items):
    return sorted(name for _, _, _, name in items)


def test_definitions_kinds_and_decorators():
    tree = ast.parse("import functools\n\n@app.route('/')\ndef page(): ...\n\n"
                     "class Box:\n    def open(self): ...\n    @property\n    def size(self): ...\n"
                     "    def outer(self):\n        def inner(): ...\n\ndef plain(): ...\n")
    found = {n: (kind, framework) for n, kind, _, framework in dcf.definitions(tree)}
    assert found == {"page": ("function", True), "Box": ("class", False),
                     "open": ("method", False), "size": ("method", False),
                     "outer": ("method", False), "plain": ("function", False)}


def test_references_cover_names_attributes_imports_strings_and_keywords():
    tree = ast.parse("from pkg import thing as alias\nx = obj.method()\nuse(flag=1)\n"
                     "getattr(a, 'dynamic_name')\n__all__ = ['exported']\nprint(plain_name)\n")
    refs = dcf.references(tree)
    assert {"thing", "alias", "obj", "method", "flag", "dynamic_name", "exported",
            "plain_name"} <= refs


def test_unused_vs_used_across_files(tmp_path):
    root = project(tmp_path, {
        "app/core.py": "def used():\n    return 1\n\ndef lonely():\n    return 2\n\n"
                       "class Report:\n    def render(self):\n        pass\n    def never(self):\n"
                       "        pass\n",
        "app/main.py": "from app.core import used, Report\n\ndef main():\n    used()\n"
                       "    Report().render()\n"})
    unused, only_tests, counts = dcf.analyse(root)
    assert names(unused) == ["lonely", "never"] and only_tests == []
    assert counts["checked"] == 5 and counts["framework"] == 0


def test_entry_points_dunders_tests_and_decorated_are_not_judged(tmp_path):
    root = project(tmp_path, {
        "m.py": "def main(): ...\ndef custom_entry(): ...\nclass A:\n    def __init__(self): ...\n"
                "@registry.register\ndef handler_fn(): ...\ndef test_something(): ...\n"
                "def really_unused(): ...\n"})
    unused, _, counts = dcf.analyse(root, entry={"custom_entry"})
    assert names(unused) == ["A", "really_unused"] and counts["framework"] == 1


def test_used_only_by_tests_is_reported_separately(tmp_path):
    root = project(tmp_path, {"lib.py": "def helper(): ...\ndef dead(): ...\n",
                              "tests/test_lib.py": "from lib import helper\n\ndef test_it():\n"
                                                   "    helper()\n"})
    unused, only_tests, _ = dcf.analyse(root)
    assert names(unused) == ["dead"] and names(only_tests) == ["helper"]


def test_string_references_keep_things_alive(tmp_path):
    root = project(tmp_path, {"plugins.py": "def load_csv(): ...\ndef load_xml(): ...\n"
                                            "HANDLERS = ['load_csv']\n"})
    assert names(dcf.analyse(root)[0]) == ["load_xml"]


def test_syntax_errors_are_skipped(tmp_path):
    root = project(tmp_path, {"good.py": "def f(): ...\n", "bad.py": "def (:\n"})
    unused, _, counts = dcf.analyse(root)
    assert names(unused) == ["f"] and counts["unparsed"] == ["bad.py"]


def test_cli_output_and_exit_codes(tmp_path, capsys):
    root = project(tmp_path, {"a.py": "def keep(): ...\ndef drop(): ...\nkeep()\n"})
    assert dcf.main([str(root)]) == 0
    out = capsys.readouterr().out
    assert "a.py:2  unused function drop" in out and "1 look unused" in out
    assert "name-based guess" in out
    assert dcf.main([str(root), "--fail-on-found"]) == 1
    assert dcf.main([str(root), "--entry", "drop", "--fail-on-found"]) == 0
    with pytest.raises(SystemExit):
        dcf.main([str(tmp_path / "missing")])
    empty = tmp_path / "empty"
    empty.mkdir()
    assert dcf.main([str(empty)]) == 1
