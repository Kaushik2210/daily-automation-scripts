import changelog_generator as cg

US = cg.US


def line(sha, day, subject):
    return f"@@{sha}{US}A{US}a@x{US}{day}{US}{subject}\n"


LOG = (line("aaaaaaa1", "2026-01-13", "feat(auth): add reset flow")
       + line("bbbbbbb2", "2026-01-12", "fix: handle empty cart.")
       + line("ccccccc3", "2026-01-12", "wip stuff")
       + line("ddddddd4", "2026-01-06", "fix!: drop Node 16"))


def test_group_commits_and_breaking():
    breaking, groups, ignored = cg.group_commits(cg.parse_log(LOG))
    assert breaking == ["drop Node 16 (ddddddd)"]
    assert groups["feat"] == ["**auth:** add reset flow (aaaaaaa)"]
    assert groups["fix"] == ["handle empty cart (bbbbbbb)", "drop Node 16 (ddddddd)"]
    assert ignored == 1


def test_render_sections_in_order():
    text = cg.render(cg.parse_log(LOG), "1.2.0", "2026-01-14")
    assert text.startswith("## [1.2.0] - 2026-01-14\n\n### BREAKING CHANGES")
    assert text.index("### Features") < text.index("### Bug fixes")
    assert "1 commit(s) without a conventional prefix were left out." in text


def test_add_to_file_prepends_under_title():
    first = cg.add_to_file("", "## [1.0.0] - 2026-01-01\n\n- a\n")
    assert first.startswith("# Changelog\n\n## [1.0.0]")
    second = cg.add_to_file(first, "## [1.1.0] - 2026-02-01\n\n- b\n")
    assert second.index("[1.1.0]") < second.index("[1.0.0]")
    assert second.startswith("# Changelog")


def test_cli_preview_and_apply(tmp_path, capsys):
    log, out = tmp_path / "log.txt", tmp_path / "CHANGELOG.md"
    log.write_text(LOG)
    base = ["--log", str(log), "--version", "1.2.0", "--date", "2026-01-14", "-o", str(out)]
    cg.main(base)
    assert not out.exists() and "### Features" in capsys.readouterr().out
    cg.main([*base, "--apply"])
    assert out.read_text(encoding="utf-8").startswith("# Changelog\n\n## [1.2.0]")
