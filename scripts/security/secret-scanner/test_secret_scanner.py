from secret_scanner import main, mask, scan_folder, scan_text

# Fake values are assembled at runtime so this file never contains a real-looking token.
AWS = "AK" + "IA" + "ABCDEFGHIJKLMNOP"
GITHUB = "gh" + "p_" + "a" * 36
PEM = "-----BEGIN " + "RSA PRIVATE KEY-----"


def test_mask():
    assert mask("short") == "short"
    assert mask(AWS) == "AKI" + "*" * 10 + "NOP"


def test_detects_each_kind():
    kinds = {k for _, k, _ in scan_text(f"key = {AWS}\ntoken: {GITHUB}\n{PEM}\n")}
    assert kinds == {"AWS access key", "GitHub token", "Private key block"}


def test_hardcoded_credential_and_placeholders():
    assert scan_text('password = "s3cr3tvalue99"')[0][1] == "Hard-coded credential"
    assert scan_text('api_key = "your_api_key_here"') == []
    assert scan_text('token = "${TOKEN_FROM_ENV}"') == []
    assert scan_text("password = os.environ['PASSWORD']") == []


def test_scan_folder_skips_git_and_binary(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text(f"x = {AWS}")
    (tmp_path / "image.bin").write_bytes(b"\xff\xfe\x00" + AWS.encode())
    (tmp_path / "app.py").write_text(f"KEY = '{AWS}'\n")
    found = list(scan_folder(tmp_path))
    assert [(p.name, n) for p, n, _, _ in found] == [("app.py", 1)]


def test_cli_exit_codes_and_masked_output(tmp_path, capsys):
    (tmp_path / "ok.txt").write_text("nothing here")
    assert main([str(tmp_path)]) == 0
    (tmp_path / "bad.txt").write_text(AWS)
    assert main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert AWS not in out and "1 possible secret(s) found." in out
