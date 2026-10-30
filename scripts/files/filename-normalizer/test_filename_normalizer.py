from filename_normalizer import main, normalize, plan_renames


def test_normalize_basic():
    assert normalize("My Holiday Photo (1).JPG") == "my_holiday_photo_1.jpg"
    assert normalize("Report - Final.v2.PDF", sep="-") == "report-final-v2.pdf"


def test_normalize_empty_stem():
    assert normalize("!!!.txt") == "file.txt"


def test_clean_names_are_not_planned(tmp_path):
    (tmp_path / "already_clean.txt").write_text("x")
    (tmp_path / "Needs Work.TXT").write_text("x")
    plan = plan_renames(tmp_path)
    assert [dst.name for _, dst in plan] == ["needs_work.txt"]


def test_apply_and_collision(tmp_path):
    (tmp_path / "A B.txt").write_text("x")
    (tmp_path / "a_b.txt").write_text("y")
    main([str(tmp_path), "--apply"])
    assert (tmp_path / "A B.txt").read_text() == "x"
    assert (tmp_path / "a_b.txt").read_text() == "y"


def test_apply_renames_file(tmp_path):
    (tmp_path / "Big File.TXT").write_text("x")
    main([str(tmp_path), "--apply"])
    assert (tmp_path / "big_file.txt").exists()
