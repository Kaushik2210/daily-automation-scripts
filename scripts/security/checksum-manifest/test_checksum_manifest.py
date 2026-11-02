from checksum_manifest import compare, main, read_manifest, scan, write_manifest


def make(tmp_path):
    (tmp_path / "a.txt").write_text("alpha")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("beta")


def test_scan_uses_relative_posix_names(tmp_path):
    make(tmp_path)
    assert sorted(scan(tmp_path)) == ["a.txt", "sub/b.txt"]


def test_manifest_round_trip_and_compare(tmp_path):
    make(tmp_path)
    recorded = read_manifest(write_manifest(scan(tmp_path)))
    (tmp_path / "a.txt").write_text("changed")
    (tmp_path / "sub" / "b.txt").unlink()
    (tmp_path / "c.txt").write_text("new")
    changed, missing, new = compare(recorded, scan(tmp_path))
    assert (changed, missing, new) == (["a.txt"], ["sub/b.txt"], ["c.txt"])


def test_create_is_dry_run_until_apply(tmp_path):
    make(tmp_path)
    main([str(tmp_path)])
    assert not (tmp_path / "SHA256SUMS.txt").exists()
    main([str(tmp_path), "--apply"])
    assert (tmp_path / "SHA256SUMS.txt").exists()


def test_verify_exit_codes_and_manifest_excluded(tmp_path, capsys):
    make(tmp_path)
    main([str(tmp_path), "--apply"])
    assert main([str(tmp_path), "--verify"]) == 0
    assert "2 file(s) checked: 0 changed" in capsys.readouterr().out
    (tmp_path / "a.txt").write_text("tampered")
    assert main([str(tmp_path), "--verify"]) == 1
    assert "CHANGED" in capsys.readouterr().out
