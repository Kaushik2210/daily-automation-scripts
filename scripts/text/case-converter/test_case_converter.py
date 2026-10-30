import pytest
from case_converter import STYLES, convert, main, split_words


def test_split_words_handles_all_input_styles():
    assert split_words("myVariableName") == ["my", "Variable", "Name"]
    assert split_words("my_variable-name here") == ["my", "variable", "name", "here"]
    assert split_words("HTTPServerError") == ["HTTP", "Server", "Error"]
    assert split_words("version2Beta") == ["version", "2", "Beta"]


@pytest.mark.parametrize("style,expected", [
    ("snake", "hello_big_world"),
    ("kebab", "hello-big-world"),
    ("camel", "helloBigWorld"),
    ("pascal", "HelloBigWorld"),
    ("title", "Hello Big World"),
    ("constant", "HELLO_BIG_WORLD"),
    ("sentence", "Hello big world"),
])
def test_convert_styles(style, expected):
    assert convert("hello big_world", style) == expected


def test_every_style_is_covered():
    assert set(STYLES) == {"snake", "kebab", "constant", "camel", "pascal", "title",
                           "sentence", "lower", "upper"}


def test_cli_converts_each_argument(capsys):
    main(["--to", "snake", "FirstName", "lastName"])
    assert capsys.readouterr().out.splitlines() == ["first_name", "last_name"]
