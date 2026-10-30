from bulk_file_renamer import find_conflicts, main, plan_renames


def make(tmp_path, *names):
    for name in names:
        (tmp_path / name).write_text("x")
    return sorted(tmp_path / n for n in names)


def test_find_replace_and_prefix(tmp_path):
    files = make(tmp_path, "holiday_001.jpg")
    plan = plan_renames(files, find="holiday", replace="trip", prefix="2026_")
    assert plan[0][1].name == "2026_trip_001.jpg"


def test_numbering(tmp_path):
    files = make(tmp_path, "a.txt", "b.txt")
    names = [dst.name for _, dst in plan_renames(files, number=True, start=5, digits=2)]
    assert names == ["a_05.txt", "b_06.txt"]


def test_conflict_detected(tmp_path):
    files = make(tmp_path, "a.txt", "b.txt")
    plan = plan_renames(files, find="b", replace="a")
    assert find_conflicts(plan)


def test_dry_run_changes_nothing(tmp_path):
    make(tmp_path, "a.txt")
    main([str(tmp_path), "--prefix", "x_"])
    assert (tmp_path / "a.txt").exists()


def test_apply_renames(tmp_path):
    make(tmp_path, "a.txt")
    main([str(tmp_path), "--prefix", "x_", "--apply"])
    assert (tmp_path / "x_a.txt").exists()
