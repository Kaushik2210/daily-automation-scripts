import ast
import json

import import_graph_builder as igb
import pytest


def project(tmp_path, files):
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return tmp_path


APP = {"app/__init__.py": "",
       "app/main.py": "import json\nimport requests\nfrom app import core, utils\n",
       "app/core.py": "from app import utils\nfrom app.models import User\n",
       "app/utils.py": "import re\nfrom app import core\n", "app/models.py": "import dataclasses\n",
       "app/legacy.py": "x = 1\n", "tests/test_core.py": "from app.core import process\n"}


def test_module_names(tmp_path):
    assert igb.module_name(tmp_path, tmp_path / "pkg" / "sub" / "mod.py") == "pkg.sub.mod"
    assert igb.module_name(tmp_path, tmp_path / "pkg" / "__init__.py") == "pkg"
    assert igb.module_name(tmp_path, tmp_path / "top.py") == "top"


def test_find_modules_skips_ignored_folders(tmp_path):
    root = project(tmp_path, {"a.py": "", ".venv/lib/x.py": "", "pkg/b.py": "",
                              "node_modules/c.py": ""})
    assert sorted(igb.find_modules(root)) == ["a", "pkg.b"]


@pytest.mark.parametrize("source,current,is_pkg,expected", [
    ("import a.b", "x.y", False, [("a.b", [])]),
    ("from a import b, c", "x", False, [("a", ["b", "c"])]),
    ("from . import sibling", "pkg.mod", False, [("pkg", ["sibling"])]),
    ("from .sibling import f", "pkg.mod", False, [("pkg.sibling", ["f"])]),
    ("from .. import up", "pkg.sub.mod", False, [("pkg", ["up"])]),
    ("from ..other import g", "pkg.sub.mod", False, [("pkg.other", ["g"])]),
    ("from .child import h", "pkg", True, [("pkg.child", ["h"])])])
def test_raw_imports_resolve_relative_forms(source, current, is_pkg, expected):
    assert list(igb.raw_imports(ast.parse(source), current, is_pkg)) == expected


def test_graph_internal_external_and_cycles(tmp_path):
    graph, external, problems = igb.build_graph(project(tmp_path, APP))
    assert problems == []
    assert graph["app.main"] == {"app.core", "app.utils"}
    assert graph["app.core"] == {"app.utils", "app.models"} and graph["app.utils"] == {"app.core"}
    assert graph["tests.test_core"] == {"app.core"} and graph["app.legacy"] == set()
    assert external["app.main"] == {"json", "requests"}
    assert igb.find_cycles(graph) == [["app.core", "app.utils"]]


def test_find_cycles_variants():
    assert igb.find_cycles({"a": {"b"}, "b": {"c"}, "c": set()}) == []
    assert igb.find_cycles({"a": {"b"}, "b": {"c"}, "c": {"a"}, "d": {"a"}}) == [["a", "b", "c"]]
    assert igb.find_cycles({"a": {"a"}}) == []  # a module importing itself is ignored


def test_syntax_errors_are_reported_not_fatal(tmp_path):
    root = project(tmp_path, {"good.py": "import os\n", "bad.py": "def (:\n"})
    graph, _, problems = igb.build_graph(root)
    assert set(graph) == {"good", "bad"} and "bad.py: can't parse" in problems[0]


def test_dot_output_marks_cycles():
    dot = igb.to_dot({"a": {"b"}, "b": {"a"}, "c": set()}, [["a", "b"]])
    assert '"a" -> "b";' in dot and '"a" [label="a", color=red];' in dot
    assert '"c" [label="c"];' in dot


def test_cli_report_exports_and_exit_codes(tmp_path, capsys):
    root = project(tmp_path / "proj", APP)
    dot, js = tmp_path / "g.dot", tmp_path / "g.json"
    assert igb.main([str(root), "--dot", str(dot), "--json", str(js)]) == 0
    out = capsys.readouterr().out
    assert "7 module(s), 6 internal import(s)" in out
    assert "app.main" in out and "requests" in out and "CYCLE: app.core <-> app.utils" in out
    assert "Third-party packages used: requests" in out and "Isolated" in out
    data = json.loads(js.read_text())
    assert data["cycles"] == [["app.core", "app.utils"]]
    core = data["modules"]["app.core"]
    assert core["imported_by"] == ["app.main", "app.utils", "tests.test_core"]
    assert "digraph imports" in dot.read_text()
    assert igb.main([str(root), "--fail-on-cycles"]) == 1
    capsys.readouterr()
    assert igb.main([str(root), "--dot", str(dot)]) == 1
    assert "already exists" in capsys.readouterr().err


def test_empty_and_missing(tmp_path, capsys):
    assert igb.main([str(tmp_path)]) == 1
    assert "No Python files" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        igb.main([str(tmp_path / "nope")])
