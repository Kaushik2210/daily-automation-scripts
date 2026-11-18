import shutil
import subprocess

import pytest
import release_tagger as rt


@pytest.mark.parametrize("message,expected", [
    ("feat: add search", ("minor", "feature")),
    ("feat(api): add search", ("minor", "feature")),
    ("fix: crash on empty input", ("patch", "fix")),
    ("perf: faster parsing", ("patch", "fix")),
    ("feat!: drop v1", ("major", "breaking")),
    ("refactor(core)!: rename things", ("major", "breaking")),
    ("fix: tweak\n\nBREAKING CHANGE: config format changed", ("major", "breaking")),
    ("docs: update readme", ("none", "other")),
    ("chore: bump deps", ("none", "other")),
    ("Update README wording", ("none", "other")),
    ("", ("none", "other"))])
def test_classify(message, expected):
    assert rt.classify(message) == expected


@pytest.mark.parametrize("current,level,new", [
    ("v1.4.2", "patch", "v1.4.3"), ("v1.4.2", "minor", "v1.5.0"), ("v1.4.2", "major", "v2.0.0"),
    ("2.0.9", "patch", "2.0.10"), ("v1.0.0", "none", "v1.0.0"),
    ("rel-3.1.0", "minor", "rel-3.2.0")])
def test_bump_version(current, level, new):
    assert rt.bump_version(current, level) == new


def test_bump_rejects_non_versions():
    with pytest.raises(ValueError):
        rt.bump_version("latest", "patch")


def test_split_log_attaches_breaking_footer():
    log = "feat: a\n\nfix: b\nBREAKING CHANGE: removed x\nchore: c\n"
    assert rt.split_log(log) == ["feat: a", "fix: b\n\nBREAKING CHANGE: removed x", "chore: c"]


def test_cli_with_log_file(tmp_path, capsys):
    log = tmp_path / "commits.txt"
    log.write_text("fix: a\nfeat(ui): b\ndocs: c\n")
    assert rt.main(["--log-file", str(log), "--current", "v1.4.2"]) == 0
    out = capsys.readouterr().out
    assert "Features:\n  - feat(ui): b" in out and "Fixes:\n  - fix: a" in out
    assert "Next version: v1.5.0  (minor bump)" in out and "Dry run" in out
    log.write_text("feat!: x\n")
    rt.main(["--log-file", str(log), "--current", "v1.4.2"])
    assert "Next version: v2.0.0  (major bump)" in capsys.readouterr().out
    log.write_text("docs: only docs\n")
    assert rt.main(["--log-file", str(log), "--current", "v1.4.2"]) == 0
    assert "no new release is needed" in capsys.readouterr().out
    log.write_text("")
    rt.main(["--log-file", str(log), "--current", "v1.4.2"])
    assert "nothing to release" in capsys.readouterr().out


def test_cli_argument_errors(tmp_path):
    log = tmp_path / "c.txt"
    log.write_text("fix: a\n")
    with pytest.raises(SystemExit):
        rt.main(["--log-file", str(log)])
    with pytest.raises(SystemExit):
        rt.main(["--log-file", str(log), "--current", "v1.0.0", "--apply"])
    assert rt.main(["--log-file", str(log), "--current", "oops"]) == 1


@pytest.mark.skipif(not shutil.which("git"), reason="git is not installed")
def test_real_repository_dry_run_and_apply(tmp_path, capsys):
    def run(*args):
        subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=T", "-c",
                        "user.email=t@example.com", "-c", "commit.gpgsign=false", *args],
                       check=True, capture_output=True)
    run("init", "-q")
    (tmp_path / "a.txt").write_text("1")
    run("add", ".")
    run("commit", "-q", "-m", "feat: first")
    run("tag", "-a", "v0.1.0", "-m", "first release")
    (tmp_path / "a.txt").write_text("2")
    run("commit", "-qam", "fix: second")
    run("commit", "-q", "--allow-empty", "-m", "feat: third")
    assert rt.main(["--repo", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "Current version: v0.1.0   (2 commit(s) since)" in out and "Next version: v0.2.0" in out
    assert rt.main(["--repo", str(tmp_path), "--apply"]) == 0
    tags = subprocess.run(["git", "-C", str(tmp_path), "tag"], capture_output=True, text=True)
    assert "v0.2.0" in tags.stdout.split()
    capsys.readouterr()
    assert rt.main(["--repo", str(tmp_path)]) == 0
    assert "No new commits since v0.2.0" in capsys.readouterr().out
