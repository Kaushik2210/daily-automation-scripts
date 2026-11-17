import readme_linter as rl

GOOD = """# Tool

A small command line tool that renames photos by the date they were taken so albums sort well.

## Features
- Fast and safe

## Install
```bash
pip install tool
```

## Usage
Run `tool photos/` and check the preview before applying the change to your files.
""" + "More detail about how it works and why it exists. " * 12 + """

## Contributing
Pull requests are welcome.

## License
MIT
"""


def statuses(text):
    issues, score = rl.analyse(text)
    return {message: status for status, message in issues}, score


def test_complete_readme_scores_high():
    found, score = statuses(GOOD)
    assert score >= 90 and "FAIL" not in found.values()


def test_missing_sections_are_reported():
    found, score = statuses("# Demo\n\nIntro text.\n\n## Usage\nRun it.\n")
    assert found["Missing the install section"] == "FAIL"
    assert found["Missing the license section"] == "FAIL"
    assert found["Missing the contributing section"] == "WARN"
    assert found["No short description under the title (what is this and who is it for?)"] == "FAIL"
    assert score < 50


def test_no_title_and_duplicates_and_skips():
    found, _ = statuses("Just text\n\n## A\n#### B\n## A\n")
    assert found["No title: start with a single '# Project name' heading"] == "FAIL"
    assert found["Heading level skipped before: B"] == "WARN"
    assert found["Duplicate headings: a"] == "WARN"


def test_empty_links_and_todo():
    found, _ = statuses("# T\n\nSee [docs]() later. TODO fix this up.\n")
    assert found["1 link(s) with an empty address"] == "FAIL"
    assert found["Placeholder text left in (TODO)"] == "WARN"


def test_code_block_headings_are_ignored():
    issues, _ = rl.analyse("# Real\n\n```\n# not a heading\n```\n")
    assert not any("top-level headings" in message for _, message in issues)


def test_cli_exit_codes(tmp_path, capsys):
    good, bad = tmp_path / "good.md", tmp_path / "bad.md"
    good.write_text(GOOD)
    bad.write_text("# Demo\n\nIntro text.\n")
    assert rl.main([str(good)]) == 0
    assert capsys.readouterr().out.startswith("good.md: score ")
    assert rl.main([str(bad)]) == 1
    assert "[FAIL] Missing the install section" in capsys.readouterr().out
    assert rl.main([str(good), "--min-score", "101"]) == 1
