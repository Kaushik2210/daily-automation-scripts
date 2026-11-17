import json

import glossary_builder as gb
import pytest

NOTES = """# Notes

- **Latency**: time for a message to travel.
- **Bandwidth** - data per second.
**TCP**: reliable delivery.
The **router** forwards packets and the **firewall** blocks traffic.
**Latency**: also called ping.
```
**Hidden**: inside code
```
"""


def test_extract_definitions_and_undefined_terms():
    definitions, others = gb.extract(NOTES)
    assert definitions == {"Latency": ["time for a message to travel.", "also called ping."],
                           "Bandwidth": ["data per second."], "TCP": ["reliable delivery."]}
    assert others == ["router", "firewall"]


def test_term_used_in_prose_and_defined_is_not_undefined():
    _, others = gb.extract("**TCP**: reliable.\nWe use **tcp** a lot.\n")
    assert others == []


def test_merge_is_case_insensitive_and_sorted():
    entries = gb.merge({"b term": ["one"], "Alpha": ["a", "again"], "B Term": ["two"]})
    assert [e["term"] for e in entries] == ["Alpha", "b term"]
    assert entries[0]["count"] == 2 and entries[1]["definition"] == "one"
    assert entries[1]["count"] == 2


def test_markdown_groups_by_letter():
    entries = gb.merge({"Apple": ["fruit"], "Avocado": ["green"], "Bean": ["seed"]})
    text = gb.render_markdown(entries, ["Zed"])
    order = [text.index(x) for x in ("## A", "**Apple**", "## B", "**Bean**")]
    assert order == sorted(order)
    assert text.count("## A") == 1 and "**Zed**  \n(no definition yet)" in text


def test_cli_formats_and_notes(tmp_path, capsys):
    notes = tmp_path / "n.md"
    notes.write_text(NOTES)
    assert gb.main([str(notes)]) == 0
    out = capsys.readouterr().out
    assert "## B" in out and "**Latency**  \ntime for a message to travel." in out
    assert "1 term(s) were defined more than once" in out
    assert "2 bold term(s) have no definition" in out
    assert gb.main([str(notes), "--format", "json", "--include-undefined"]) == 0
    data = json.loads(capsys.readouterr().out.split("\n\n")[0])
    assert data[0] == {"term": "Bandwidth", "definition": "data per second."}
    assert {"term": "router", "definition": ""} in data
    assert gb.main([str(notes), "--format", "csv"]) == 0
    assert capsys.readouterr().out.startswith("term,definition\nBandwidth,data per second.\n")


def test_output_file_and_errors(tmp_path, capsys):
    notes = tmp_path / "n.md"
    notes.write_text(NOTES)
    target = tmp_path / "glossary.md"
    assert gb.main([str(notes), "-o", str(target)]) == 0
    assert target.read_text().startswith("# Glossary")
    assert gb.main([str(notes), "-o", str(target)]) == 1
    empty = tmp_path / "e.md"
    empty.write_text("nothing bold here")
    assert gb.main([str(empty)]) == 1
    with pytest.raises(SystemExit):
        gb.main([str(tmp_path / "gone.md")])
