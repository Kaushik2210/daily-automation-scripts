import shutil
import subprocess
from datetime import date

import pytest
import repo_health_scorer as rhs

WORDS = "Some words about the project. " * 25
README = f"# Demo\n\n{WORDS}\n\n## Install\n\nrun it\n\n## Usage\n\ngo\n"


def make(tmp_path, files):
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return tmp_path


FULL = {"README.md": README, "LICENSE": "MIT", "tests/test_a.py": "def test_a(): pass\n",
        ".github/workflows/ci.yml": "on: push\n", ".gitignore": "*.pyc\n",
        "requirements.txt": "pytest\n", "CONTRIBUTING.md": "hi", "CHANGELOG.md": "# log",
        "SECURITY.md": "report here", "src/app.py": "x = 1\n"}


def checks_of(tmp_path, files, age=None):
    return {name: (got, most) for name, got, most, _ in
            rhs.score(rhs.scan(make(tmp_path, files)), age)}


def test_a_complete_project_scores_full_marks(tmp_path):
    result = checks_of(tmp_path, FULL)
    assert all(got == most for got, most in result.values())
    assert sum(g for g, _ in result.values()) == 90


def test_an_empty_project_scores_only_for_no_junk(tmp_path):
    result = checks_of(tmp_path, {"main.py": "print(1)\n"})
    assert {n: g for n, (g, _) in result.items() if g} == {"No junk committed": 5}


def test_each_missing_piece_loses_its_points(tmp_path):
    for missing, check in [("LICENSE", "License"), (".gitignore", ".gitignore"),
                           ("CONTRIBUTING.md", "CONTRIBUTING"), ("CHANGELOG.md", "CHANGELOG"),
                           ("requirements.txt", "Dependencies listed")]:
        files = {k: v for k, v in FULL.items() if k != missing}
        result = checks_of(tmp_path / missing.replace(".", "_"), files)
        assert result[check][0] == 0, check


def test_readme_quality_levels(tmp_path):
    short = checks_of(tmp_path / "a", {**FULL, "README.md": "# Tiny\n"})
    assert short["README"][0] == 10 and short["README detail"][0] == 0
    assert short["README install/usage"][0] == 0
    assert checks_of(tmp_path / "b", FULL)["README install/usage"][0] == 5


def test_test_and_ci_detection_variants(tmp_path):
    js = checks_of(tmp_path / "js", {"src/a.test.ts": "x", ".gitlab-ci.yml": "x"})
    assert js["Tests"][0] == 15 and js["CI"][0] == 15
    go = checks_of(tmp_path / "go", {"pkg/util_test.go": "x", "Jenkinsfile": "x"})
    assert go["Tests"][0] == 15 and go["CI"][0] == 15
    assert checks_of(tmp_path / "none", {"a.py": "x"})["Tests"][0] == 0


def test_junk_is_found_but_ignored_folders_are_not_scanned(tmp_path):
    facts = rhs.scan(make(tmp_path, {"app.py": "x", "__pycache__/a.pyc": "x", ".env": "A=1",
                                     "node_modules/pkg/index.js": "x", ".git/config": "x",
                                     "sub/.DS_Store": "x"}))
    assert set(facts["junk"]) == {".env", "sub/.DS_Store", "__pycache__", "node_modules"}
    hidden = rhs.scan(make(tmp_path / "ignored", {".gitignore": "__pycache__/\n.env\n",
                                                  ".env": "A=1", "app.py": "x"}))
    assert hidden["junk"] == []
    assert facts["file_count"] >= 1


def test_activity_points_and_grades():
    facts = {"readme": None, "readme_words": 0, "readme_headings": [], "license": None,
             "tests": [], "ci": [], "gitignore": False, "manifest": None, "contributing": None,
             "changelog": None, "community": None, "junk": []}
    ages = {n: dict((c[0], c[1]) for c in rhs.score(facts, n))["Recent activity"]
            for n in (10, 200, 1000)}
    assert ages == {10: 10, 200: 5, 1000: 0}
    assert [rhs.grade(p) for p in (95, 80, 65, 45, 10)] == ["A", "B", "C", "D", "F"]


def test_cli(tmp_path, capsys):
    good = make(tmp_path / "good", FULL)
    assert rhs.main([str(good)]) == 0
    out = capsys.readouterr().out
    assert "health 100% (grade A)" in out and "[PASS] License" in out and "90 of 90 points" in out
    bad = make(tmp_path / "bad", {"a.py": "x"})
    assert rhs.main([str(bad)]) == 1
    assert "[MISS] License" in capsys.readouterr().out
    assert rhs.main([str(bad), "--min-score", "0"]) == 0
    with pytest.raises(SystemExit):
        rhs.main([str(tmp_path / "missing")])


@pytest.mark.skipif(not shutil.which("git"), reason="git is not installed")
def test_git_activity(tmp_path, capsys, monkeypatch):
    for key, value in (("NAME", "T"), ("EMAIL", "t@example.com")):
        monkeypatch.setenv(f"GIT_AUTHOR_{key}", value)
        monkeypatch.setenv(f"GIT_COMMITTER_{key}", value)
    repo = make(tmp_path / "r", {"a.py": "x"})
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "first"], check=True)
    assert rhs.last_commit_age(repo) == 0
    assert rhs.last_commit_age(repo, today=date(2099, 1, 1)) > 10000
    rhs.main([str(repo), "--git", "--min-score", "0"])
    assert "Recent activity" in capsys.readouterr().out
    plain = make(tmp_path / "plain", {"a.py": "x"})
    rhs.main([str(plain), "--git", "--min-score", "0"])
    assert "No git history found" in capsys.readouterr().out
