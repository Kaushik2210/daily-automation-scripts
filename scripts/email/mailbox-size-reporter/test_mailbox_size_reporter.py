import mailbox_size_reporter as msr
import pytest

SMALL = "From a@x.test Mon Sep 01 08:00:00 2026\nFrom: A <a@x.test>\nSubject: 1\n\nhello\n"
BIG = SMALL + "\nFrom b@x.test Tue Sep 02 08:00:00 2026\nFrom: B <b@x.test>\nSubject: 2\n\n" + (
    "x" * 3000 + "\n")


class FakeIMAP:
    def __init__(self, folders):
        self.folders, self.current, self.calls = folders, None, []

    def list(self):
        names = [b'(\\HasNoChildren) "/" "%s"' % name.encode() for name in self.folders]
        return "OK", names + [b'(\\Noselect) "/" "[Gmail]"']

    def select(self, folder, readonly=False):
        self.calls.append(("select", folder, readonly))
        name = folder.strip('"')
        if name not in self.folders:
            return "NO", [b"nope"]
        self.current = name
        return "OK", [str(len(self.folders[name])).encode()]

    def fetch(self, rng, what):
        self.calls.append(("fetch", rng, what))
        sizes = self.folders[self.current]
        return "OK", [b"%d (RFC822.SIZE %d)" % (i + 1, s) for i, s in enumerate(sizes)]

    def logout(self):
        pass


def test_human_size():
    assert [msr.human_size(n) for n in (0, 1536, 3 * 1024 ** 4)] == ["0 B", "1.5 KB", "3.0 TB"]


def test_mbox_report_counts_and_sizes(tmp_path):
    (tmp_path / "small.mbox").write_text(SMALL)
    (tmp_path / "big.mbox").write_text(BIG)
    rows = msr.mbox_report([tmp_path / "small.mbox", tmp_path / "big.mbox"])
    assert [(n, c) for n, c, _ in rows] == [("small.mbox", 1), ("big.mbox", 2)]
    assert rows[1][2] > 3000 > rows[0][2]


def test_sorted_rows():
    rows = [("b", 5, 100), ("A", 9, 50), ("c", 5, 300)]
    assert [r[0] for r in msr.sorted_rows(rows, "size")] == ["c", "b", "A"]
    assert [r[0] for r in msr.sorted_rows(rows, "count")] == ["A", "b", "c"]
    assert [r[0] for r in msr.sorted_rows(rows, "name")] == ["A", "b", "c"]


def test_cli_prints_a_table_with_totals(tmp_path, capsys):
    (tmp_path / "small.mbox").write_text(SMALL)
    (tmp_path / "big.mbox").write_text(BIG)
    args = ["--mbox", str(tmp_path / "small.mbox"), "--mbox", str(tmp_path / "big.mbox")]
    assert msr.main(args) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].split() == ["Folder", "Messages", "Size"]
    assert lines[1].startswith("big.mbox") and lines[-1].split()[:2] == ["Total", "3"]


def test_imap_sums_sizes_read_only_and_skips_empty_folders():
    fake = FakeIMAP({"INBOX": [100, 200, 300], "Empty": [], "Sent": [1024]})
    assert msr.imap_report(fake, None) == [("INBOX", 3, 600), ("Empty", 0, 0), ("Sent", 1, 1024)]
    assert all(c[2] is True for c in fake.calls if c[0] == "select")
    assert [c for c in fake.calls if c[0] == "fetch"][0][1:] == ("1:*", "(RFC822.SIZE)")
    assert sum(c[0] == "fetch" for c in fake.calls) == 2  # none for the empty folder


def test_imap_cli_with_folder_choice(monkeypatch, capsys):
    fake = FakeIMAP({"INBOX": [100], "Sent": [2048]})
    monkeypatch.setattr(msr, "connect", lambda: fake)
    assert msr.main(["--folder", "Sent"]) == 0
    out = capsys.readouterr().out
    assert "Sent" in out and "INBOX" not in out and "2.0 KB" in out


def test_errors(monkeypatch, capsys):
    fake = FakeIMAP({"INBOX": [1]})
    monkeypatch.setattr(msr, "connect", lambda: fake)
    assert msr.main(["--folder", "Missing"]) == 1
    assert "couldn't open folder" in capsys.readouterr().err
    monkeypatch.undo()
    monkeypatch.delenv("IMAP_HOST", raising=False)
    assert msr.main([]) == 1
    with pytest.raises(SystemExit):
        msr.main(["--mbox", "gone.mbox"])
