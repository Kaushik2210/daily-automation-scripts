from folder_organizer import folder_for, main, plan_moves


def test_category_lookup(tmp_path):
    assert folder_for(tmp_path / "a.PNG") == "images"
    assert folder_for(tmp_path / "a.xyz") == "other"
    assert folder_for(tmp_path / "a.pdf", by_extension=True) == "pdf"
    assert folder_for(tmp_path / "README", by_extension=True) == "no_extension"


def test_plan_ignores_folders_and_hidden(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / ".hidden").write_text("x")
    (tmp_path / "sub").mkdir()
    assert [src.name for src, _ in plan_moves(tmp_path)] == ["a.txt"]


def test_dry_run_leaves_files(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    main([str(tmp_path)])
    assert (tmp_path / "a.txt").exists()


def test_apply_moves_files(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "b.mp3").write_text("x")
    main([str(tmp_path), "--apply"])
    assert (tmp_path / "documents" / "a.txt").exists()
    assert (tmp_path / "audio" / "b.mp3").exists()
