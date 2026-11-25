import os
import shutil
import subprocess

import git_hook_installer as ghi
import pytest

HAVE_SH = shutil.which("sh") is not None


def repo(tmp_path):
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    return tmp_path


def run(tmp_path, *args):
    return ghi.main([*args, "--repo", str(tmp_path), "--hooks-dir", str(tmp_path / ".git/hooks")])


def test_render_each_hook():
    pre = ghi.render("pre-commit", ["ruff check .", "pytest -q"])
    assert pre.startswith("#!/bin/sh\n# managed by git-hook-installer") and "set -e" in pre
    assert "ruff check . || {" in pre and 'echo "pre-commit: pytest -q"' in pre
    assert "nothing configured" in ghi.render("pre-push", [])
    assert "grep -Eq" in ghi.render("commit-msg", []) and "feat|fix" in ghi.render("commit-msg", [])
    assert "main|master" in ghi.render("protect-branch", [])
    with pytest.raises(ValueError):
        ghi.render("post-everything", [])
    assert ghi.hook_file("protect-branch") == "pre-commit"
    assert ghi.hook_file("pre-push") == "pre-push"


def test_dry_run_changes_nothing(tmp_path, capsys):
    root = repo(tmp_path)
    assert run(root, "install", "commit-msg", "pre-commit", "--preset", "python") == 0
    out = capsys.readouterr().out
    assert "would install  commit-msg" in out and "Dry run" in out
    assert list((root / ".git/hooks").iterdir()) == []


def test_install_writes_executable_hooks_and_keeps_foreign_ones(tmp_path, capsys):
    root = repo(tmp_path)
    mine = root / ".git/hooks/commit-msg"
    mine.write_text("#!/bin/sh\necho someone elses\n")
    assert run(root, "install", "commit-msg", "pre-commit", "--command", "echo ok", "--apply") == 0
    hooks = root / ".git/hooks"
    assert ghi.is_ours(hooks / "commit-msg") and ghi.is_ours(hooks / "pre-commit")
    assert (hooks / "commit-msg.bak").read_text() == "#!/bin/sh\necho someone elses\n"
    assert "echo ok" in (hooks / "pre-commit").read_text()
    if os.name != "nt":  # Windows has no executable bit
        assert (hooks / "commit-msg").stat().st_mode & 0o100
    capsys.readouterr()
    assert run(root, "install", "commit-msg", "--apply") == 0  # reinstalling replaces ours
    assert "replaces an older copy" in capsys.readouterr().out
    assert not (hooks / "commit-msg.bak.1").exists()


def test_second_foreign_backup_gets_a_number(tmp_path):
    root = repo(tmp_path)
    hook = root / ".git/hooks/pre-push"
    for round_ in range(2):
        hook.write_text(f"#!/bin/sh\necho foreign {round_}\n")
        run(root, "install", "pre-push", "--apply")
    hooks = root / ".git/hooks"
    assert (hooks / "pre-push.bak").exists() and (hooks / "pre-push.bak.1").exists()


def test_uninstall_only_removes_our_hooks(tmp_path, capsys):
    root = repo(tmp_path)
    run(root, "install", "commit-msg", "--apply")
    (root / ".git/hooks/pre-push").write_text("#!/bin/sh\nforeign\n")
    assert run(root, "uninstall", "commit-msg") == 0
    assert (root / ".git/hooks/commit-msg").exists()  # dry run
    assert run(root, "uninstall", "commit-msg", "--apply") == 0
    assert not (root / ".git/hooks/commit-msg").exists()
    assert run(root, "uninstall", "pre-push", "--apply") == 1
    assert (root / ".git/hooks/pre-push").exists()
    assert "wasn't installed by this tool" in capsys.readouterr().out


def test_list_shows_installed_hooks(tmp_path, capsys):
    root = repo(tmp_path)
    run(root, "install", "commit-msg", "--apply")
    (root / ".git/hooks/pre-commit.sample").write_text("#!/bin/sh\n")
    (root / ".git/hooks/post-merge").write_text("#!/bin/sh\n")
    capsys.readouterr()
    assert run(root, "list") == 0
    out = capsys.readouterr().out
    assert "commit-msg" in out and "installed by this tool" in out
    assert "pre-commit.sample" in out and "sample" in out and "post-merge" in out and "other" in out


def test_argument_errors(tmp_path, capsys):
    root = repo(tmp_path)
    with pytest.raises(SystemExit):
        run(root, "install", "nonsense")
    with pytest.raises(SystemExit):
        run(root, "install")
    assert ghi.main(["install", "commit-msg", "--repo", str(tmp_path / "nope")]) == 1
    assert "doesn't look like a git repository" in capsys.readouterr().err


@pytest.mark.skipif(not HAVE_SH, reason="no sh available")
def test_commit_msg_hook_really_enforces_the_format(tmp_path):
    root = repo(tmp_path)
    run(root, "install", "commit-msg", "--apply")
    hook = root / ".git/hooks/commit-msg"

    def verdict(message):
        note = tmp_path / "msg.txt"
        note.write_text(message + "\n")
        return subprocess.run(["sh", str(hook), str(note)], capture_output=True).returncode

    assert [verdict(m) for m in ["feat: add search", "fix(api)!: handle nulls", "Merge branch x",
                                 "added stuff", "feat:nospace", "feat: ", "chore: bump"]] == [
        0, 0, 0, 1, 1, 1, 0]


@pytest.mark.skipif(not HAVE_SH, reason="no sh available")
def test_pre_commit_hook_runs_the_checks(tmp_path):
    root = repo(tmp_path)
    run(root, "install", "pre-commit", "--command", "true", "--apply")
    assert subprocess.run(["sh", str(root / ".git/hooks/pre-commit")]).returncode == 0
    run(root, "install", "pre-commit", "--command", "true", "--command", "false", "--apply")
    assert subprocess.run(["sh", str(root / ".git/hooks/pre-commit")],
                          capture_output=True).returncode == 1
