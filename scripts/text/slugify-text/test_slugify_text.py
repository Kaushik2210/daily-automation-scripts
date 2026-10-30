from slugify_text import main, slugify, unique_slugs


def test_basic_and_accents():
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("Crème Brûlée & Café") == "creme-brulee-and-cafe"
    assert slugify("  --Many   spaces--  ") == "many-spaces"


def test_separator_and_case():
    assert slugify("My Great Post", sep="_") == "my_great_post"
    assert slugify("My Great Post", keep_case=True) == "My-Great-Post"


def test_max_length_does_not_cut_words():
    assert slugify("one two three four", max_length=12) == "one-two"
    assert slugify("abcdefghij", max_length=4) == "abcd"


def test_duplicates_are_numbered(capsys):
    assert unique_slugs(["Intro", "intro", "Intro!"]) == ["intro", "intro-2", "intro-3"]
    main(["Hello World", "Hello World"])
    assert capsys.readouterr().out.splitlines() == ["hello-world", "hello-world-2"]
