import pytest
from inflection import pluralize
from inflection import singularize

@pytest.fixture
def uncountable_words():
    """Nouns that have no distinct plural form and must be returned unchanged."""
    return ["sheep", "fish", "series", "species", "equipment", "information", "rice", "money", "jeans", "police"]

@pytest.fixture
def already_plural_words():
    """Words that are already plural; pluralizing them must be a no-op."""
    return ["posts", "cats", "quizzes", "categories", "octopi", "matrices", "mice", "boxes", "analyses", "data"]

def test_pluralize_regular_word_appends_s():
    """A plain noun gets a simple trailing 's'."""
    assert pluralize("cat") == "cats"
    assert pluralize("post") == "posts"
    assert pluralize("book") == "books"

@pytest.mark.parametrize(
    "word, expected",
    [
        ("posts", "posts"),
        ("octopus", "octopi"),
        ("sheep", "sheep"),
        ("CamelOctopus", "CamelOctopi"),
    ],
)
def test_pluralize_docstring_examples_are_honored(word, expected):
    """Each documented example of pluralize behaves exactly as advertised."""
    assert pluralize(word) == expected

@pytest.mark.parametrize(
    "word",
    ["sheep", "fish", "series", "species", "equipment", "information", "rice", "money", "jeans", "police"],
)
def test_pluralize_uncountable_word_is_returned_unchanged(word):
    """Words whose lowercase form is uncountable are returned verbatim."""
    assert pluralize(word) == word

@pytest.mark.parametrize("word", ["Sheep", "SHEEP", "Fish", "Series"])
def test_pluralize_uncountable_check_ignores_case(word):
    """Uncountable detection is case-insensitive and preserves the original casing."""
    result = pluralize(word)

    assert result == word
    assert result.lower() == word.lower()

def test_pluralize_empty_string_returns_empty_string():
    """The empty string is falsy so it is returned unchanged instead of becoming 's'."""
    result = pluralize("")

    assert result == ""
    assert len(result) == 0

@pytest.mark.parametrize("value", [None, 0, False, (), [], {}, set()])
def test_pluralize_falsy_non_string_values_are_returned_unchanged(value):
    """Falsy input of any type is echoed back without raising."""
    result = pluralize(value)

    assert result is value

@pytest.mark.parametrize(
    "plural_word",
    ["posts", "cats", "quizzes", "categories", "octopi", "matrices", "mice", "boxes", "analyses", "data"],
)
def test_pluralize_of_already_plural_word_is_stable(plural_word):
    """Pluralize is idempotent: pluralize(pluralize(w)) == pluralize(w)."""
    assert pluralize(plural_word) == plural_word

@pytest.mark.parametrize(
    "word, expected",
    [
        ("box", "boxes"),
        ("match", "matches"),
        ("kiss", "kisses"),
        ("dish", "dishes"),
        ("alias", "aliases"),
        ("status", "statuses"),
        ("axis", "axes"),
        ("testis", "testes"),
        ("bus", "buses"),
    ],
)
def test_pluralize_words_ending_in_sibilant_add_es(word, expected):
    """Sibilant endings trigger the 'es' pluralization rule."""
    assert pluralize(word) == expected

@pytest.mark.parametrize(
    "word, expected",
    [
        ("category", "categories"),
        ("baby", "babies"),
        ("company", "companies"),
        ("query", "queries"),
    ],
)
def test_pluralize_consonant_y_ends_with_ies(word, expected):
    """Consonant + 'y' words are pluralized with 'ies'."""
    assert pluralize(word) == expected

@pytest.mark.parametrize("word", ["day", "key", "boy", "monkey"])
def test_pluralize_vowel_y_ends_with_just_s(word):
    """Vowel + 'y' words simply gain an 's'."""
    result = pluralize(word)

    assert result == word + "s"
    assert not result.endswith("ies")

@pytest.mark.parametrize(
    "word, expected",
    [
        ("quiz", "quizzes"),
        ("quizzes", "quizzes"),
        ("ox", "oxen"),
        ("oxen", "oxen"),
        ("mouse", "mice"),
        ("mice", "mice"),
        ("Mouse", "Mice"),
        ("house", "houses"),
    ],
)
def test_pluralize_irregular_and_classical_forms(word, expected):
    """Irregular/classical plurals are handled by dedicated rules."""
    assert pluralize(word) == expected

@pytest.mark.parametrize(
    "word, expected",
    [
        ("matrix", "matrices"),
        ("vertex", "vertices"),
        ("index", "indices"),
        ("virus", "viri"),
        ("viri", "viri"),
        ("hive", "hives"),
    ],
)
def test_pluralize_latin_greek_loanwords(word, expected):
    """Latin/Greek loanwords use their traditional irregular plurals."""
    assert pluralize(word) == expected

@pytest.mark.parametrize(
    "word, expected",
    [
        ("datum", "data"),
        ("medium", "media"),
        ("analysis", "analyses"),
        ("tomato", "tomatoes"),
        ("potato", "potatoes"),
    ],
)
def test_pluralize_latin_suffix_replacements(word, expected):
    """Latin-style suffix rules are applied for -um, -sis and -o words."""
    assert pluralize(word) == expected

@pytest.mark.parametrize(
    "word, expected",
    [
        ("knife", "knives"),
        ("life", "lives"),
        ("wife", "wives"),
        ("half", "halves"),
    ],
)
def test_pluralize_f_and_fe_endings_become_ves(word, expected):
    """Words ending in f/fe (or lf/rf) take the 'ves' ending."""
    assert pluralize(word) == expected

@pytest.mark.parametrize(
    "word, expected",
    [
        ("CamelOctopus", "CamelOctopi"),
        ("Category", "Categories"),
        ("Mouse", "Mice"),
        ("Sheep", "Sheep"),
    ],
)
def test_pluralize_preserves_leading_capitalization(word, expected):
    """Case is preserved for the part of the word that is not pluralized."""
    result = pluralize(word)

    assert result == expected
    assert result[0] == word[0]

def test_pluralize_handles_non_ascii_word():
    """Non-ASCII words are pluralized without losing their original characters."""
    result = pluralize("café")

    assert isinstance(result, str)
    assert result.startswith("café")
    assert result.endswith("s")

@pytest.mark.parametrize("word", ["", "octopus", "posts", "sheep", "SHEEP", "café"])
def test_pluralize_always_returns_a_string_for_string_input(word):
    """For string input the function always yields a string back."""
    assert isinstance(pluralize(word), str)

def test_pluralize_does_not_modify_input_word():
    """The input string is left untouched (the plural is a new string)."""
    word = "octopus"
    result = pluralize(word)

    assert word == "octopus"
    assert result == "octopi"
    assert result is not word

@pytest.mark.parametrize("word", ["cat", "octopus", "category", "box", "knife"])
def test_pluralize_round_trips_with_singularize(word):
    """pluralize(singularize(word)) gives back the plural of the word."""
    plural = pluralize(word)

    assert singularize(plural) == word
    assert pluralize(singularize(plural)) == plural

@pytest.mark.parametrize("value", [42, ["octopus"], {"word": "octopus"}, 3.5])
def test_pluralize_non_string_truthy_input_raises_attribute_error(value):
    """Truthy non-string input raises AttributeError (no implicit coercion)."""
    with pytest.raises(AttributeError):
        pluralize(value)

def test_pluralize_matches_the_docstring_example_without_state_leakage():
    """Calling pluralize repeatedly yields identical results."""
    results = [pluralize("octopus") for _ in range(5)]

    assert results == ["octopi"] * 5
