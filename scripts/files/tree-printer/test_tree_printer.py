from tree_printer import ASCII, build_tree, main


def make(tmp_path):
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "mod.py").write_text("x")
    (tmp_path / "src" / "main.py").write_text("x")
    (tmp_path / "README.md").write_text("x")
    (tmp_path / ".git").mkdir()


def test_full_tree_ascii(tmp_path):
    make(tmp_path)
    lines = build_tree(tmp_path, chars=ASCII)
    assert lines[1:] == [
        "|-- src",
        "|   |-- pkg",
        "|   |   `-- mod.py",
        "|   `-- main.py",
        "`-- README.md",
    ]


def test_depth_limit(tmp_path):
    make(tmp_path)
    lines = build_tree(tmp_path, max_depth=1, chars=ASCII)
    assert not any("mod.py" in line for line in lines)
    assert any("src" in line for line in lines)


def test_hidden_and_dirs_only(tmp_path):
    make(tmp_path)
    assert any(".git" in line for line in build_tree(tmp_path, show_hidden=True))
    dirs = build_tree(tmp_path, dirs_only=True, chars=ASCII)
    assert not any("README" in line for line in dirs)


def test_cli_runs(tmp_path, capsys):
    make(tmp_path)
    assert main([str(tmp_path), "--ascii", "-d", "1"]) == 0
    assert "README.md" in capsys.readouterr().out
