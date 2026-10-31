from env_var_lister import is_secret, list_vars, main, mask

ENV = {"HOME": "/home/me", "API_TOKEN": "abcdef123456", "path": "/usr/bin", "MY_PASSWORD": "pw"}


def test_is_secret():
    assert is_secret("GITHUB_TOKEN") and is_secret("db_password")
    assert not is_secret("HOME")


def test_mask_hides_but_hints_length():
    assert mask("pw") == "****"
    assert mask("abcdef123456") == "ab********56"
    assert "cdef" not in mask("abcdef123456")


def test_list_masks_and_sorts_case_insensitively():
    rows = list_vars(ENV)
    assert [n for n, _ in rows] == ["API_TOKEN", "HOME", "MY_PASSWORD", "path"]
    assert dict(rows)["API_TOKEN"] == "ab********56"
    assert dict(list_vars(ENV, show_secrets=True))["API_TOKEN"] == "abcdef123456"


def test_search_matches_name_or_value():
    assert [n for n, _ in list_vars(ENV, "usr")] == ["path"]
    assert [n for n, _ in list_vars(ENV, "home")] == ["HOME"]


def test_cli_names_only(monkeypatch, capsys):
    monkeypatch.setattr("env_var_lister.os.environ", ENV)
    main(["token", "--names-only"])
    assert capsys.readouterr().out.strip() == "API_TOKEN"
