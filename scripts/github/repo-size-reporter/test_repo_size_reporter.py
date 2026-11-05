import repo_size_reporter as rs


def make_repo(root):
    (root / "src").mkdir()
    (root / "src" / "big.bin").write_bytes(b"x" * 3000)
    (root / "src" / "small.py").write_text("print(1)\n")
    (root / "README.md").write_text("hello")
    (root / ".git").mkdir()
    (root / ".git" / "objects").mkdir()
    (root / ".git" / "objects" / "pack").write_bytes(b"y" * 500)
    (root / "node_modules").mkdir()
    (root / "node_modules" / "dep.js").write_bytes(b"z" * 9999)


def test_human_size():
    assert rs.human_size(10) == "10 B" and rs.human_size(1536) == "1.5 KB"
    assert rs.human_size(3 * 1024**3) == "3.0 GB"


def test_measure_separates_git_and_skips_dependencies(tmp_path):
    make_repo(tmp_path)
    report = rs.measure(tmp_path)
    names = [rel for _, rel in report["files"]]
    assert names[0] == "src/big.bin" and "node_modules/dep.js" not in names
    assert not any(n.startswith(".git/") for n in names)
    assert report["git_bytes"] == 500 and report["skipped_dirs"] == 1
    assert report["by_ext"][".bin"] == (1, 3000)


def test_include_deps_counts_everything(tmp_path):
    make_repo(tmp_path)
    names = [rel for _, rel in rs.measure(tmp_path, include_deps=True)["files"]]
    assert "node_modules/dep.js" in names


def test_cli_report(tmp_path, capsys):
    make_repo(tmp_path)
    rs.main([str(tmp_path), "-n", "2"])
    out = capsys.readouterr().out
    assert "Working tree:" in out and ".git history: 500 B" in out
    assert "src/big.bin" in out and "Largest 2 file(s):" in out
    assert "(skipped 1 dependency folder(s)" in out


def test_empty_folder(tmp_path, capsys):
    rs.main([str(tmp_path)])
    assert "Working tree: 0 B in 0 file(s)" in capsys.readouterr().out
