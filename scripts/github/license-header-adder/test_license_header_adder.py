import license_header_adder as lha
import pytest

LINES = ["Copyright (c) 2026 Ada", "Licensed under MIT.", "SPDX-License-Identifier: MIT"]


def test_header_lines_for_known_licenses():
    mit = lha.header_lines("mit", "Ada", "2026")
    assert mit[0] == "Copyright (c) 2026 Ada" and mit[-1] == "SPDX-License-Identifier: MIT"
    assert lha.header_lines("apache-2.0", "X", "1")[-1].endswith("Apache-2.0")
    assert lha.header_lines("mit", "X", "1", custom="\nMy own\ntext\n") == ["My own", "text"]


@pytest.mark.parametrize("suffix,first,last", [
    (".py", "# Copyright (c) 2026 Ada", "# SPDX-License-Identifier: MIT"),
    (".js", "// Copyright (c) 2026 Ada", "// SPDX-License-Identifier: MIT"),
    (".sql", "-- Copyright (c) 2026 Ada", "-- SPDX-License-Identifier: MIT"),
    (".css", "/*", " */"), (".html", "<!--", "-->")])
def test_comment_styles(suffix, first, last):
    block = lha.comment_block(LINES, lha.STYLES[suffix])
    assert block[0] == first and block[-1] == last


def test_python_header_goes_after_the_shebang_and_encoding_line():
    source = "#!/usr/bin/env python\n# -*- coding: utf-8 -*-\nimport os\n"
    result = lha.add_header(source, ".py", LINES)
    assert result.splitlines()[:2] == ["#!/usr/bin/env python", "# -*- coding: utf-8 -*-"]
    assert result.splitlines()[2] == "# Copyright (c) 2026 Ada"
    assert result.endswith("# SPDX-License-Identifier: MIT\n\nimport os\n")


def test_plain_file_gets_a_header_and_a_blank_line():
    assert lha.add_header("print(1)\n", ".py", LINES) == (
        "# Copyright (c) 2026 Ada\n# Licensed under MIT.\n# SPDX-License-Identifier: MIT\n\n"
        "print(1)\n")
    assert lha.add_header("", ".py", LINES).endswith("MIT\n")


def test_existing_headers_are_detected():
    for text in ("# SPDX-License-Identifier: MIT\nx = 1\n", "// Copyright 2020 Someone\nx\n",
                 '"""Module.\n\nLicensed under the Apache License.\n"""\n'):
        assert lha.has_header(text)
        assert lha.add_header(text, ".py", LINES) is None
    assert not lha.has_header("x = 1\n" * 30 + "# copyright far below\n")


def test_xml_declaration_stays_first():
    result = lha.add_header('<?xml version="1.0"?>\n<root/>\n', ".xml", LINES)
    assert result.splitlines()[0] == '<?xml version="1.0"?>' and result.splitlines()[1] == "<!--"


def test_windows_line_endings_are_kept():
    result = lha.add_header("a = 1\r\nb = 2\r\n", ".py", LINES)
    assert "\r\n" in result and "\n" not in result.replace("\r\n", "")


def test_cli_dry_run_then_apply(tmp_path, capsys):
    (tmp_path / "a.py").write_text("print('a')\n")
    (tmp_path / "b.js").write_text("// Copyright (c) 2020 Old\nconsole.log(1)\n")
    (tmp_path / "notes.txt").write_text("not source")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "lib.js").write_text("x")
    (tmp_path / "bad.py").write_bytes(b"\xff\xfe\x00bad")
    assert lha.main([str(tmp_path), "--holder", "Ada", "--year", "2026"]) == 0
    out = capsys.readouterr().out
    assert "would add" in out and "has header" in out and "unreadable" in out
    assert "node_modules" not in out and "notes.txt" not in out
    assert (tmp_path / "a.py").read_text() == "print('a')\n"
    assert lha.main([str(tmp_path), "--holder", "Ada", "--year", "2026", "--apply"]) == 0
    assert (tmp_path / "a.py").read_text().startswith("# Copyright (c) 2026 Ada\n")
    assert lha.main([str(tmp_path), "--apply"]) == 0
    assert (tmp_path / "a.py").read_text().count("SPDX") == 1  # a second run adds nothing


def test_ext_filter_and_errors(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b.js").write_text("y = 2\n")
    lha.main([str(tmp_path), "--ext", "py", "--apply"])
    assert "SPDX" in (tmp_path / "a.py").read_text()
    assert "SPDX" not in (tmp_path / "b.js").read_text()
    with pytest.raises(SystemExit):
        lha.main([str(tmp_path), "--ext", "exe"])
    with pytest.raises(SystemExit):
        lha.main([str(tmp_path / "missing")])
