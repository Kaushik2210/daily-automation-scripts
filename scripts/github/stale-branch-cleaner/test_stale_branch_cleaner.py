import os
import shutil
import subprocess
from datetime import date

import pytest
import stale_branch_cleaner as sbc

US = "\x1f"
REFS = "\n".join(US.join(p) for p in [
    ("main", "2026-11-01", "Ann", "latest"),
    ("feat/old-merged", "2026-05-01", "Ann", "done"),
    ("feat/recent-merged", "2026-11-01", "Bob", "done"),
    ("feat/old-open", "2026-04-01", "Cy", "wip"),
    ("develop", "2025-01-01", "Ann", "dev"),
    ("fix/ancient", "2025-06-01", "Bob", "fix"),
    ("weird", "not-a-date", "Bob", "?")]) + "\n"
MERGED = "* main\n  feat/old-merged\n  feat/recent-merged\n  develop\n  fix/ancient\n+ weird\n"
TODAY = date(2026, 11, 9)


def test_parse_refs_and_prefix_stripping():
    branches = sbc.parse_refs(f"origin/a{US}2026-01-01{US}Ann{US}s\norigin/HEAD{US}{US}{US}\n",
                              "origin/")
    assert branches == [{"name": "a", "date": "2026-01-01", "author": "Ann", "subject": "s"}]


def test_parse_merged_ignores_markers_and_head_pointers():
    text = "* main\n  feat/x\n+ wt\n  origin/HEAD -> origin/main\n  origin/old\n"
    assert sbc.parse_merged(text) == {"main", "feat/x", "wt", "origin/old"}
    assert sbc.parse_merged(text, "origin/") == {"main", "feat/x", "wt", "old"}


def test_select_candidates_needs_merged_old_and_unprotected():
    chosen, skipped = sbc.select_candidates(sbc.parse_refs(REFS), sbc.parse_merged(MERGED),
                                            TODAY, 90)
    assert [b["name"] for b in chosen] == ["fix/ancient", "feat/old-merged"]  # oldest first
    reasons = dict(skipped)
    assert reasons["main"] == "protected" and reasons["develop"] == "protected"
    assert "not merged" in reasons["feat/old-open"]
    assert "only 8 day(s) old" in reasons["feat/recent-merged"]
    assert "no readable commit date" in reasons["weird"]


def test_offline_files_are_a_dry_run(tmp_path, capsys):
    refs, merged = tmp_path / "refs.txt", tmp_path / "merged.txt"
    refs.write_text(REFS)
    merged.write_text(MERGED)
    args = ["--refs", str(refs), "--merged", str(merged), "--today", "2026-11-09"]
    assert sbc.main(args) == 0
    out = capsys.readouterr().out
    assert "2 stale merged local branch(es)" in out and "feat/old-merged" in out
    assert "Dry run - nothing deleted" in out
    with pytest.raises(SystemExit):
        sbc.main(["--refs", str(refs)])
    with pytest.raises(SystemExit):
        sbc.main([*args, "--apply"])


needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")


def run(repo, *args, date_text=None):
    env = {**os.environ, "GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": "t@x.test",
           "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": "t@x.test"}
    if date_text:
        env["GIT_COMMITTER_DATE"] = env["GIT_AUTHOR_DATE"] = date_text
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)


@pytest.fixture
def repo(tmp_path):
    run(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "f.txt").write_text("1")
    run(tmp_path, "add", ".")
    run(tmp_path, "commit", "-q", "-m", "first", date_text="2025-01-01T10:00:00")
    run(tmp_path, "branch", "old-merged")
    run(tmp_path, "checkout", "-q", "-b", "old-open")
    (tmp_path / "f.txt").write_text("2")
    run(tmp_path, "commit", "-qam", "unmerged work", date_text="2025-01-02T10:00:00")
    run(tmp_path, "checkout", "-q", "main")
    return tmp_path


@needs_git
def test_real_repo_dry_run_then_apply(repo, capsys):
    base = ["--repo", str(repo), "--today", "2026-11-09"]
    assert sbc.main(base) == 0
    out = capsys.readouterr().out
    assert "1 stale merged local branch(es)" in out and "old-merged" in out
    assert "old-open" not in out
    branches = sbc.git(repo, "branch", "--format=%(refname:short)")
    assert "old-merged" in branches  # still there after a dry run
    assert sbc.main([*base, "--apply"]) == 0
    assert "deleted old-merged" in capsys.readouterr().out
    left = sbc.git(repo, "branch", "--format=%(refname:short)").split()
    assert sorted(left) == ["main", "old-open"]


@needs_git
def test_not_a_repo_is_reported(tmp_path, capsys):
    assert sbc.main(["--repo", str(tmp_path / "nowhere")]) == 1
    assert "Couldn't read the branches" in capsys.readouterr().err
