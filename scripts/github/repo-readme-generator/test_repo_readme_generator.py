import json

import repo_readme_generator as rg


def make_node_project(root):
    (root / "src").mkdir()
    (root / "src" / "app.js").write_text("x")
    (root / "src" / "util.js").write_text("x")
    (root / "main.py").write_text("x")
    (root / "node_modules").mkdir()
    (root / "node_modules" / "skip.js").write_text("x")
    (root / "package.json").write_text(json.dumps({
        "name": "shop", "description": "A shop", "license": "MIT",
        "scripts": {"start": "node src/app.js", "test": "jest"}}))


def test_detect_reads_package_json_and_languages(tmp_path):
    make_node_project(tmp_path)
    info = rg.detect(tmp_path)
    assert info["name"] == "shop" and info["license"] == "MIT"
    assert info["languages"] == ["JavaScript", "Python"]     # node_modules is ignored
    assert "node_modules/" not in info["tree"]


def test_render_node_project(tmp_path):
    make_node_project(tmp_path)
    text = rg.render(rg.detect(tmp_path))
    assert text.startswith("# shop\n\nA shop")
    assert "npm install\nnpm start\nnpm run test" in text
    assert "src/\n  app.js" in text and "## License\n\nMIT." in text


def test_python_and_empty_projects(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests\n")
    (tmp_path / "LICENSE").write_text("MIT License\n\nCopyright\n")
    text = rg.render(rg.detect(tmp_path))
    assert "pip install -r requirements.txt" in text and "MIT License." in text
    empty = rg.render(rg.detect(tmp_path / "."))
    assert "## Project structure" in empty


def test_cli_preview_apply_and_no_overwrite(tmp_path, capsys):
    make_node_project(tmp_path)
    out = tmp_path / "README.md"
    rg.main([str(tmp_path), "-o", str(out)])
    assert not out.exists() and "# shop" in capsys.readouterr().out
    assert rg.main([str(tmp_path), "-o", str(out), "--apply"]) == 0
    assert rg.main([str(tmp_path), "-o", str(out), "--apply"]) == 1
