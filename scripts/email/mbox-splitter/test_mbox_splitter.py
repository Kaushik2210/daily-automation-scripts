import mailbox

import mbox_splitter as ms
import pytest

MBOX = """From a@x.test Mon Sep 01 08:00:00 2026
From: A <a@x.test>
Subject: sep one
Date: Tue, 01 Sep 2026 08:00:00 +0000

first

From a@x.test Wed Sep 30 23:00:00 2026
From: A <a@x.test>
Subject: sep two
Date: Wed, 30 Sep 2026 23:00:00 +0000

second
>From stuff quoted here

From b@x.test Thu Oct 01 01:00:00 2026
From: B <b@x.test>
Subject: oct
Date: Thu, 01 Oct 2026 01:00:00 +0000

third

From c@x.test Fri Nov 06 10:00:00 2026
From: C <c@x.test>
Subject: no date header

fourth

From d@x.test Sat Jan 01 10:00:00 2027
From: D <d@x.test>
Subject: bad date
Date: not a date

fifth

From e@x.test garbled
From: E <e@x.test>
Subject: no usable date

sixth
"""


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "all.mbox"
    path.write_text(MBOX)
    return path


def test_month_of_uses_date_header_then_from_line_then_unknown():
    dated = mailbox.mboxMessage(
        "From a@x.test Mon Sep 01 08:00:00 2026\nDate: Tue, 01 Sep 2026 08:00:00 +0000\n\nx")
    assert ms.month_of(dated) == "2026-09"
    undated = mailbox.mboxMessage("From a@x.test Fri Nov 06 10:00:00 2026\nSubject: x\n\ny")
    assert ms.month_of(undated) == "2026-11"


def test_group_by_month(source):
    groups = ms.group_by_month(mailbox.mbox(str(source)))
    assert {month: len(keys) for month, keys in groups.items()} == {
        "2026-09": 2, "2026-10": 1, "2026-11": 1, "2027-01": 1, "unknown-date": 1}
    assert list(groups) == sorted(groups)


def test_dry_run_writes_nothing(source, tmp_path, capsys):
    out = tmp_path / "pieces"
    assert ms.main([str(source), "--out-dir", str(out)]) == 0
    text = capsys.readouterr().out
    assert "2026-09.mbox: 2 message(s)" in text and "would write" in text and "Dry run" in text
    assert not out.exists()


def test_apply_writes_each_month_and_leaves_the_source_alone(source, tmp_path, capsys):
    out, before = tmp_path / "pieces", source.read_bytes()
    assert ms.main([str(source), "--out-dir", str(out), "--apply", "--prefix", "mail-"]) == 0
    assert sorted(p.name for p in out.iterdir()) == [
        "mail-2026-09.mbox", "mail-2026-10.mbox", "mail-2026-11.mbox", "mail-2027-01.mbox",
        "mail-unknown-date.mbox"]
    september = mailbox.mbox(str(out / "mail-2026-09.mbox"))
    assert [m["Subject"] for m in september] == ["sep one", "sep two"]
    assert ">From stuff quoted here" in september[1].get_payload()
    assert source.read_bytes() == before
    assert "Split 6 message(s) into 5 new file(s)" in capsys.readouterr().out


def test_existing_files_are_never_overwritten(source, tmp_path, capsys):
    out = tmp_path / "pieces"
    out.mkdir()
    (out / "2026-10.mbox").write_text("precious")
    assert ms.main([str(source), "--out-dir", str(out), "--apply"]) == 0
    assert (out / "2026-10.mbox").read_text() == "precious"
    assert "skipped" in capsys.readouterr().out and (out / "2026-09.mbox").exists()


def test_default_output_is_next_to_the_source_and_errors(source, tmp_path, capsys):
    assert ms.main([str(source), "--apply"]) == 0
    assert (tmp_path / "2026-09.mbox").exists()
    empty = tmp_path / "empty.mbox"
    empty.write_text("")
    assert ms.main([str(empty)]) == 1
    with pytest.raises(SystemExit):
        ms.main([str(tmp_path / "gone.mbox")])
