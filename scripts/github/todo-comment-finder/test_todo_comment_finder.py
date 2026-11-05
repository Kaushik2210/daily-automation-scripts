import todo_comment_finder as tf

PATTERN = tf.make_pattern(tf.DEFAULT_TAGS)


def test_finds_tags_in_many_comment_styles():
    text = "\n".join([
        "x = 1  # TODO: fix this",
        "// FIXME(ada) handle null",
        "/* HACK: temporary */",
        "<!-- todo remove -->",
        "-- XXX sql cleanup",
        "plain TODO in a string is ignored",
    ])
    found = tf.scan_text(text, PATTERN)
    assert [(n, t) for n, t, _, _ in found] == [(1, "TODO"), (2, "FIXME"), (3, "HACK"),
                                                (4, "TODO"), (5, "XXX")]
    assert found[1][2] == "ada"
    assert found[2][3] == "temporary" and found[3][3] == "remove"


def test_custom_tags_and_word_boundaries():
    pattern = tf.make_pattern(["NOTE"])
    assert tf.scan_text("# NOTE: keep", pattern)[0][1] == "NOTE"
    assert tf.scan_text("# NOTEBOOK stuff", pattern) == []


def test_scan_folder_skips_dirs_and_binaries(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("# TODO: one\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "b.js").write_text("// TODO: ignored\n")
    (tmp_path / "bin.dat").write_bytes(b"\xff\xfe\x00# TODO: binary")
    found = list(tf.scan_folder(tmp_path, tf.DEFAULT_TAGS))
    assert [(p.name, n) for p, n, *_ in found] == [("a.py", 1)]


def test_cli_owner_filter_and_summary(tmp_path, capsys):
    (tmp_path / "a.js").write_text("// TODO(ada): x\n// TODO(lin): y\n// FIXME: z\n")
    tf.main([str(tmp_path), "--owner", "ada"])
    out = capsys.readouterr().out
    assert "a.js:1  TODO (ada)  x" in out and "lin" not in out
    assert "1 comment(s) found: 1 TODO." in out
    tf.main([str(tmp_path)])
    assert "3 comment(s) found: 2 TODO, 1 FIXME." in capsys.readouterr().out
