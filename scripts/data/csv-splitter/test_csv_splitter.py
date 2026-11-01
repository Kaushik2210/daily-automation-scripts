from csv_splitter import chunks, main, part_name, split_file


def test_chunks_and_names():
    assert list(chunks(range(5), 2)) == [[0, 1], [2, 3], [4]]
    assert list(chunks([], 3)) == []
    assert part_name("big", 7) == "big_part007.csv"


def make_csv(path, rows):
    path.write_text("id,name\n" + "".join(f"{i},n{i}\n" for i in range(rows)))


def test_split_dry_run_writes_nothing(tmp_path):
    src = tmp_path / "data.csv"
    make_csv(src, 5)
    parts = split_file(src, 2, tmp_path)
    assert [c for _, c in parts] == [2, 2, 1]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["data.csv"]


def test_apply_repeats_header(tmp_path):
    src = tmp_path / "data.csv"
    make_csv(src, 3)
    main([str(src), "--rows", "2", "-o", str(tmp_path / "out"), "--apply"])
    first = (tmp_path / "out" / "data_part001.csv").read_text().splitlines()
    second = (tmp_path / "out" / "data_part002.csv").read_text().splitlines()
    assert first == ["id,name", "0,n0", "1,n1"]
    assert second == ["id,name", "2,n2"]


def test_empty_file_has_no_parts(tmp_path):
    src = tmp_path / "empty.csv"
    src.write_text("")
    assert split_file(src, 10, tmp_path) == []
