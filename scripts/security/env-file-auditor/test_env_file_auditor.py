from pathlib import Path

from env_file_auditor import audit, gitignored, main, parse_env

SAMPLE = """# comment
API_KEY=short
DB_PASSWORD=admin
export SECRET_TOKEN="a-long-and-fine-value-123"
EMPTY=
NAME=your_name_here
API_KEY=again
"""


def test_parse_env_handles_export_quotes_comments():
    entries = parse_env(SAMPLE)
    assert [n for _, n, _ in entries][:4] == ["API_KEY", "DB_PASSWORD", "SECRET_TOKEN", "EMPTY"]
    assert dict((n, v) for _, n, v in entries)["SECRET_TOKEN"] == "a-long-and-fine-value-123"


def test_audit_finds_each_problem_without_leaking_values():
    problems = audit(parse_env(SAMPLE))
    text = " | ".join(f"{n}:{p}" for _, n, p in problems)
    assert "API_KEY:looks like a weak secret" in text
    assert "DB_PASSWORD:looks like a weak secret" in text
    assert "EMPTY:is empty" in text and "NAME:still holds a placeholder" in text
    assert "duplicate of line 2" in text
    assert "admin" not in text and "short" not in text


def test_example_comparison_and_gitignore():
    problems = audit(parse_env("A=12345678\n"), {"A", "B"})
    assert (0, "B", "is in the example file but missing here") in problems
    assert gitignored(Path(".env"), "node_modules\n.env\n")
    assert not gitignored(Path(".env"), "node_modules\n")


def test_cli_exit_codes(tmp_path, capsys):
    good = tmp_path / ".env"
    good.write_text("TOKEN=averyLongSecretValue\n")
    assert main([str(good)]) == 0
    good.write_text("TOKEN=\n")
    assert main([str(good)]) == 1
    assert "is empty" in capsys.readouterr().out
