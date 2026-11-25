import json
import shutil
import subprocess

import changed_files_finder as cff
import pytest

DIFF = ("M\tapps/web/src/app.tsx\nA\tapps/api/users.py\nD\tapps/api/old.py\n"
        "R087\tlibs/shared/a.py\tlibs/shared/b.py\nM\tREADME.md\nM\tdocs/guide.md\n\nbad line\n")


def test_parse_name_status():
    changes = cff.parse_name_status(DIFF)
    assert [c["status"] for c in changes] == ["modified", "added", "deleted", "renamed",
                                              "modified", "modified"]
    renamed = changes[3]
    assert renamed["path"] == "libs/shared/b.py" and renamed["old_path"] == "libs/shared/a.py"
    assert cff.parse_name_status("") == []


@pytest.mark.parametrize("path,patterns,expected", [
    ("apps/web/src/a.ts", ["apps/*", "libs/*"], "apps/web"),
    ("libs/shared/x.py", ["apps/*", "libs/*"], "libs/shared"),
    ("README.md", ["apps/*"], "(root)"), ("docs/guide.md", ["apps/*"], None),
    ("apps/readme.md", ["apps/*"], None), ("tools/a/b.sh", ["tools"], "tools")])
def test_project_of(path, patterns, expected):
    assert cff.project_of(path, patterns) == expected


def test_grouping_and_rename_counts_for_both_projects():
    changes = cff.parse_name_status("R\tlibs/a/x.py\tapps/web/x.py\nM\tdocs/g.md\nM\tTOP.md\n")
    groups = cff.group(changes, ["apps/*", "libs/*"])
    assert list(groups) == ["(root)", "apps/web", "docs", "libs/a"]
    assert len(groups["apps/web"]) == 1 and len(groups["libs/a"]) == 1


def test_dependents_are_added_with_reasons():
    uses = {"libs/shared": ["apps/web", "apps/api"], "apps/web": ["apps/e2e"]}
    affected, reasons = cff.add_dependents(["libs/shared"], uses)
    assert affected == ["apps/api", "apps/web", "libs/shared"]
    assert reasons == {"apps/web": "depends on libs/shared", "apps/api": "depends on libs/shared"}
    assert cff.add_dependents(["apps/web"], {"libs/shared": ["apps/web"]}) == (["apps/web"], {})


def test_cli_text_json_paths_and_filters(tmp_path, capsys):
    diff = tmp_path / "d.txt"
    diff.write_text(DIFF)
    base = ["--from-file", str(diff), "--projects", "apps/*", "libs/*"]
    assert cff.main(base + ["--depends", "libs/shared=apps/web,apps/mobile"]) == 0
    out = capsys.readouterr().out
    assert "6 changed file(s) in saved diff d.txt" in out and "apps/api  (2)" in out
    assert "renamed      libs/shared/b.py (from libs/shared/a.py)" in out
    assert "apps/mobile  (depends on libs/shared)" in out and "apps/web  (depends" not in out
    assert "1 added, 1 deleted, 3 modified, 1 renamed." in out
    assert cff.main(base + ["--format", "projects"]) == 0
    assert capsys.readouterr().out.split() == ["apps/api", "apps/web", "docs", "libs/shared"]
    assert cff.main(base + ["--format", "paths", "--ext", "py", "--exclude", "libs/*"]) == 0
    assert capsys.readouterr().out.split() == ["apps/api/users.py"]
    assert cff.main(base + ["--format", "json", "--exclude", "docs/*"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert "docs/guide.md" not in data["files"] and "libs/shared" in data["projects"]
    with pytest.raises(SystemExit):
        cff.main(["--from-file", str(diff), "--depends", "nonsense"])


def test_missing_file_and_empty_diff(tmp_path, capsys):
    assert cff.main(["--from-file", str(tmp_path / "none.txt")]) == 1
    assert "Can't get the changes" in capsys.readouterr().err
    empty = tmp_path / "e.txt"
    empty.write_text("")
    assert cff.main(["--from-file", str(empty)]) == 0
    assert "No changes." in capsys.readouterr().out


@pytest.mark.skipif(not shutil.which("git"), reason="git is not installed")
def test_real_repository(tmp_path, capsys, monkeypatch):
    for key, value in (("NAME", "T"), ("EMAIL", "t@example.com")):
        monkeypatch.setenv(f"GIT_AUTHOR_{key}", value)
        monkeypatch.setenv(f"GIT_COMMITTER_{key}", value)

    def git(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

    git("init", "-q", "-b", "main")
    (tmp_path / "apps/web").mkdir(parents=True)
    (tmp_path / "apps/web/a.txt").write_text("1")
    (tmp_path / "README.md").write_text("r")
    git("add", ".")
    git("commit", "-q", "-m", "base")
    git("checkout", "-q", "-b", "feature")
    (tmp_path / "apps/web/a.txt").write_text("2")
    (tmp_path / "apps/new.txt").write_text("n")
    git("add", ".")
    git("commit", "-q", "-m", "change")
    (tmp_path / "untracked.txt").write_text("u")
    assert cff.main(["--repo", str(tmp_path), "--ref", "main", "--projects", "apps/*"]) == 0
    out = capsys.readouterr().out
    assert "2 changed file(s) in main...HEAD" in out and "apps/web  (1)" in out
    assert "untracked.txt" not in out
    cff.main(["--repo", str(tmp_path), "--ref", "main", "--include-uncommitted",
              "--format", "paths"])
    assert "untracked.txt" in capsys.readouterr().out
    assert cff.main(["--repo", str(tmp_path), "--ref", "no-such-ref"]) == 1
