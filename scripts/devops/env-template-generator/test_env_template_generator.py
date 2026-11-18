import env_template_generator as eg
import pytest

ENV = """# Database
DB_HOST=localhost
DB_PASSWORD="s3cret value"
export API_KEY=abc123   # production key
DEBUG=true
PORT=8080
DATABASE_URL=postgres://user:pw@db:5432/app
EMPTY=

NAME=My App
"""


def test_all_values_removed_by_default_comments_kept():
    template, keys, blanked = eg.convert(ENV)
    assert template.splitlines()[0] == "# Database"
    assert "DB_HOST=\n" in template and "export API_KEY=\n" in template and "s3cret" not in template
    assert keys == ["DB_HOST", "DB_PASSWORD", "API_KEY", "DEBUG", "PORT", "DATABASE_URL", "EMPTY",
                    "NAME"]
    assert "EMPTY" not in blanked and "NAME" in blanked and len(blanked) == 7


def test_keep_safe_keeps_only_harmless_values():
    template, _, blanked = eg.convert(ENV, keep_safe=True)
    assert "DB_HOST=localhost" in template and "DEBUG=true" in template and "PORT=8080" in template
    assert "DB_PASSWORD=\n" in template and "API_KEY=\n" in template
    assert "DATABASE_URL=\n" in template and "NAME=\n" in template
    assert "pw" not in template and sorted(blanked) == [
        "API_KEY", "DATABASE_URL", "DB_PASSWORD", "NAME"]


def test_placeholder():
    template, _, _ = eg.convert("TOKEN=abc\nPORT=80\n", placeholder="changeme")
    assert template == "TOKEN=changeme\nPORT=changeme\n"


def test_credentials_in_urls_are_secret_even_if_name_is_harmless():
    assert eg.is_secret("DATABASE_URL", "postgres://u:p@h/db") and not eg.is_secret("HOST", "x")
    assert eg.is_secret("SECRET_KEY", "x") and not eg.is_secret("PORT", "80")


def test_cli_dry_run_apply_and_drift_check(tmp_path, capsys):
    env = tmp_path / "app.env"
    env.write_text(ENV)
    assert eg.main([str(env)]) == 0
    assert "Dry run" in capsys.readouterr().out and not (tmp_path / "app.env.example").exists()
    assert eg.main([str(env), "--apply", "--keep-safe"]) == 0
    assert "DEBUG=true" in (tmp_path / "app.env.example").read_text()
    capsys.readouterr()
    assert eg.main([str(env), "--apply"]) == 0
    assert "same variables" in capsys.readouterr().out
    env.write_text(ENV + "NEW_VAR=1\n")
    assert eg.main([str(env), "--apply"]) == 1
    assert "Missing from it: NEW_VAR" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        eg.main([str(tmp_path / "none.env")])
