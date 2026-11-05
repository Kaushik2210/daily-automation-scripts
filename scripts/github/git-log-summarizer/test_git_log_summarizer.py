import git_log_summarizer as gl

US = gl.US


def line(sha, name, day, subject):
    return f"@@{sha}{US}{name}{US}x@x.com{US}{day}{US}{subject}\n"


LOG = (line("1", "Ada Lovelace", "2026-01-13", "feat: login")
       + line("2", "Lin Chen", "2026-01-12", "fix(cart): empty")
       + line("3", "Ada Lovelace", "2026-01-05", "docs: guide")
       + line("4", "Max Weber", "2026-01-05", "wip stuff"))


def test_week_label_iso():
    assert gl.week_label("2026-01-05") == "2026-W02"
    assert gl.week_label("2026-01-01") == "2026-W01"
    assert gl.week_label("2025-12-29") == "2026-W01"   # ISO week belongs to the next year


def test_commit_type():
    assert gl.commit_type("feat(ui)!: x") == "feat" and gl.commit_type("FIX: y") == "fix"
    assert gl.commit_type("random words") == "other"


def test_summarize_counts():
    summary = gl.summarize(gl.parse_log(LOG))
    assert summary["authors"]["Ada Lovelace"] == 2
    assert list(summary["weeks"]) == ["2026-W02", "2026-W03"]
    assert summary["weeks"]["2026-W02"]["Max Weber"] == 1
    assert summary["types"] == {"feat": 1, "fix": 1, "docs": 1, "other": 1}


def test_cli_output_and_empty(tmp_path, capsys):
    f = tmp_path / "log.txt"
    f.write_text(LOG)
    gl.main(["--log", str(f)])
    out = capsys.readouterr().out
    assert "4 commit(s) by 3 author(s)" in out and "2026-W03" in out and "By type" in out
    f.write_text("")
    gl.main(["--log", str(f)])
    assert "No commits found." in capsys.readouterr().out
