import subprocess

import pytest
from publish_site import branch_exists, git, publish


@pytest.fixture
def remote(tmp_path, monkeypatch):
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "Test")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@example.com")
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "--quiet", str(bare)], check=True)
    seed = tmp_path / "seed"
    seed.mkdir()
    git("init", "--quiet", cwd=seed)
    (seed / "README.md").write_text("main branch")
    git("add", "-A", cwd=seed)
    git("commit", "--quiet", "-m", "seed", cwd=seed)
    git("push", "--quiet", str(bare), "HEAD:refs/heads/main", cwd=seed)
    return str(bare)


def make_site(path, files):
    path.mkdir(exist_ok=True)
    for old in path.iterdir():
        old.unlink()
    for name, text in files.items():
        (path / name).write_text(text, encoding="utf-8")
    return path


def files_on_branch(remote, clone, branch="gh-pages"):
    subprocess.run(["git", "clone", "--quiet", "--branch", branch, remote, str(clone)], check=True)
    return sorted(p.name for p in clone.iterdir() if p.name != ".git")


def test_first_publish_creates_branch_with_only_site_files(remote, tmp_path):
    site = make_site(tmp_path / "site", {"index.html": "<h1>hi</h1>", ".nojekyll": ""})
    assert not branch_exists(remote, "gh-pages", tmp_path)
    assert publish(site, remote) == "pushed"
    # the README from the main branch must not leak into the site branch
    assert files_on_branch(remote, tmp_path / "first") == [".nojekyll", "index.html"]


def test_unchanged_and_update_removes_old_files(remote, tmp_path):
    site = make_site(tmp_path / "site", {"index.html": "v1", "old.html": "x"})
    publish(site, remote)
    assert publish(site, remote) == "unchanged"
    site = make_site(tmp_path / "site", {"index.html": "v2"})
    assert publish(site, remote) == "pushed"
    assert files_on_branch(remote, tmp_path / "second") == ["index.html"]


def test_dry_run_changes_nothing(remote, tmp_path):
    site = make_site(tmp_path / "site", {"index.html": "v1"})
    assert publish(site, remote, push=False) == "dry-run"
    assert not branch_exists(remote, "gh-pages", tmp_path)
