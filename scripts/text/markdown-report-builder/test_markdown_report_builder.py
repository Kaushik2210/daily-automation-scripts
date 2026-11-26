from datetime import date

import markdown_report_builder as mrb
import pytest


def test_natural_order_and_exclusions(tmp_path):
    for name in ("10-outro.md", "2-middle.md", "1-intro.md", "draft.md", "notes.txt"):
        (tmp_path / name).write_text("x")
    names = [f.name for f in mrb.collect([tmp_path], ["draft*"])]
    assert names == ["1-intro.md", "2-middle.md", "10-outro.md"]
    with pytest.raises(FileNotFoundError):
        mrb.collect([tmp_path / "missing"], [])


def test_front_matter():
    meta, body = mrb.split_front_matter("---\ntitle: \"Hi there\"\nAuthor: Me\n---\n# Body\n")
    assert meta == {"title": "Hi there", "author": "Me"} and body == "# Body"
    assert mrb.split_front_matter("# No meta") == ({}, "# No meta")
    assert mrb.split_front_matter("---\nnever closed\n")[0] == {}


def test_slug_is_unique():
    used = {}
    assert [mrb.slug("Results & More!", used), mrb.slug("Results", used),
            mrb.slug("Results", used)] == ["results--more", "results", "results-1"]


def test_headings_skip_code_blocks_and_deep_levels():
    text = "# One\n```\n# not a heading\n```\n## Two\n### Three\n"
    assert mrb.headings(text, 2) == [(1, "One"), (2, "Two")]
    assert mrb.headings(text, 3)[-1] == (3, "Three")


def test_build_with_toc_and_front_matter(tmp_path):
    (tmp_path / "1.md").write_text("---\ntitle: Weekly\nauthor: Team\n---\n# Summary\n\nText\n")
    (tmp_path / "2.md").write_text("---\ntitle: Ignored\n---\n# Results\n\n## Detail\n")
    files = mrb.collect([tmp_path], [])
    text, used = mrb.build(files, None, None, date(2026, 11, 23), True, 2)
    assert text.startswith("# Weekly\n\n*Team | 2026-11-23*\n\n## Contents")
    assert "- [Summary](#summary)" in text and "  - [Detail](#detail)" in text
    assert "title: Ignored" not in text and used == ["1.md", "2.md"]
    assert mrb.build(files, "Custom", "Me", date(2026, 1, 1), False, 2)[0].startswith(
        "# Custom\n\n*Me | 2026-01-01*\n\n# Summary")


def test_cli_output_and_overwrite_protection(tmp_path, capsys):
    (tmp_path / "a.md").write_text("# A\n")
    out = tmp_path / "report.md"
    assert mrb.main([str(tmp_path / "a.md"), "--output", str(out), "--date", "2026-11-23"]) == 0
    assert "Wrote" in capsys.readouterr().out and out.read_text().startswith("# Report")
    assert mrb.main([str(tmp_path / "a.md"), "--output", str(out)]) == 1
    assert mrb.main([str(tmp_path / "a.md"), "--output", str(out), "--force"]) == 0


def test_cli_errors(tmp_path, capsys):
    assert mrb.main([str(tmp_path / "nope")]) == 1
    assert "Can't build the report" in capsys.readouterr().err
    (tmp_path / "x.md").write_text("# X\n")
    assert mrb.main([str(tmp_path), "--exclude", "*.md"]) == 1
    assert "No markdown files" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        mrb.main([str(tmp_path), "--toc-depth", "9"])
    with pytest.raises(SystemExit):
        mrb.main([str(tmp_path), "--date", "later"])
