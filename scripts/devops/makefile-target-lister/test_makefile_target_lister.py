import makefile_target_lister as mtl
import pytest

MAKEFILE = """# Project tasks
.PHONY: help install test build clean

##@ Development
install: ## Install the dependencies
\tpip install -r requirements.txt

test: install ## Run the tests
\tpytest

# Build the package
build: test
\tpython -m build

##@ Housekeeping
clean:
\trm -rf dist

VERSION := 1.0
%.o: %.c
\tcc -c $<
app.bin: main.c util.c ## Compile the app
\tcc -o $@ $^
"""


def by_name():
    targets, phony = mtl.parse(MAKEFILE)
    return {t["name"]: t for t in targets}, phony


def test_targets_docs_and_sections():
    targets, phony = by_name()
    assert list(targets) == ["install", "test", "build", "clean", "app.bin"]
    assert targets["install"]["doc"] == "Install the dependencies"
    assert targets["install"]["section"] == "Development"
    assert targets["test"]["deps"] == ["install"] and targets["test"]["doc"] == "Run the tests"
    assert targets["build"]["doc"] == "Build the package"  # from the comment above it
    assert targets["clean"]["doc"] == "" and targets["clean"]["section"] == "Housekeeping"
    assert phony == {"help", "install", "test", "build", "clean"}


def test_ignores_variables_pattern_rules_and_recipe_lines():
    targets, _ = by_name()
    assert "VERSION" not in targets and "%.o" not in targets and ".PHONY" not in targets


def test_multiple_targets_on_one_line():
    targets, _ = mtl.parse("a b: ## both\n\techo\n")
    assert [(t["name"], t["doc"]) for t in targets] == [("a", "both"), ("b", "both")]


def test_cli_default_and_all(tmp_path, capsys):
    path = tmp_path / "Makefile"
    path.write_text(MAKEFILE)
    assert mtl.main([str(path)]) == 0
    out = capsys.readouterr().out
    assert "Development" in out and "install  Install the dependencies" in out
    assert "test     Run the tests  (needs: install)" in out
    assert "clean" not in out and "1 without a description hidden" in out
    assert "app.bin" in out and "[file target]" in out
    assert mtl.main([str(path), "--all"]) == 0
    assert "(no description)" in capsys.readouterr().out


def test_no_documented_targets_and_missing_file(tmp_path, capsys):
    path = tmp_path / "Makefile"
    path.write_text("all:\n\techo hi\n")
    assert mtl.main([str(path)]) == 1
    assert "No documented targets" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        mtl.main([str(tmp_path / "nope")])
