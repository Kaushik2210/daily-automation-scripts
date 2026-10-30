from empty_folder_cleaner import find_empty_dirs, main


def test_nested_empty_dirs_found_deepest_first(tmp_path):
    (tmp_path / "a" / "b").mkdir(parents=True)
    found = find_empty_dirs(tmp_path)
    assert found == [tmp_path / "a" / "b", tmp_path / "a"]


def test_folder_with_file_is_kept(tmp_path):
    (tmp_path / "keep").mkdir()
    (tmp_path / "keep" / "f.txt").write_text("x")
    (tmp_path / "empty").mkdir()
    assert find_empty_dirs(tmp_path) == [tmp_path / "empty"]


def test_dry_run_keeps_folders(tmp_path):
    (tmp_path / "empty").mkdir()
    main([str(tmp_path)])
    assert (tmp_path / "empty").exists()


def test_apply_removes_nested(tmp_path):
    (tmp_path / "a" / "b").mkdir(parents=True)
    main([str(tmp_path), "--apply"])
    assert not (tmp_path / "a").exists()
    assert tmp_path.exists()
