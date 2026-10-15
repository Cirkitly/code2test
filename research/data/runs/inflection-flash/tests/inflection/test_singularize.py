import pytest
from inflection import singularize
from inflection import pluralize

@pytest.fixture
def documented_examples():
    """(word, expected singular) pairs taken from the singularize docstring."""
    return [
        ("posts", "post"),
        ("octopi", "octopus"),
        ("sheep", "sheep"),
        ("word", "word"),
        ("CamelOctopi", "CamelOctopus"),
    ]

@pytest.fixture
def plural_round_trips():
    """(singular, plural) pairs where pluralize/singularize must round-trip."""
    return [
        ("post", "posts"),
        ("octopus", "octopi"),
        ("sheep", "sheep"),
        ("word", "words"),
        ("CamelOctopus", "CamelOctopi"),
    ]

def test_singularize_returns_singular_form_of_a_regular_plural():
    """A regular English plural is converted back to its singular form."""
    assert singularize("posts") == "post"

def test_singularize_converts_irregular_octopi_to_octopus():
    """Irregular '-i' plurals are rewritten to the '-us' singular."""
    assert singularize("octopi") == "octopus"

def test_singularize_leaves_uncountable_sheep_unchanged():
    """Uncountable nouns have no distinct singular form."""
    assert singularize("sheep") == "sheep"

def test_singularize_leaves_already_singular_word_unchanged():
    """A word that is already singular is not modified."""
    assert singularize("word") == "word"

def test_singularize_preserves_leading_capitalization():
    """Capitalization of the untouched part of the word is preserved."""
    assert singularize("CamelOctopi") == "CamelOctopus"

def test_singularize_matches_rules_case_insensitively():
    """Inflection rules are matched regardless of letter case."""
    # The internal 'i' -> 'us' rule matches regardless of case and only the
    # matched suffix is rewritten, so the capitalised prefix survives.
    assert singularize("Octopi") == "Octopus"
    # The trailing plural marker is stripped no matter how it is cased.
    assert singularize("POSTS").lower() == "post"

@pytest.mark.parametrize(
    ("plural", "expected_singular"),
    [
        ("boxes", "box"),
        ("churches", "church"),
        ("dishes", "dish"),
        ("classes", "class"),
        ("buses", "bus"),
        ("shoes", "shoe"),
    ],
)
def test_singularize_converts_plurals_ending_in_es(plural, expected_singular):
    """'-es' plurals (sibilant stems, bus, shoe) lose their plural suffix."""
    assert singularize(plural) == expected_singular

@pytest.mark.parametrize(
    ("plural", "expected_singular"),
    [
        ("cities", "city"),
        ("parties", "party"),
    ],
)
def test_singularize_converts_plurals_ending_in_ies(plural, expected_singular):
    """Consonant + '-ies' plurals collapse to a '-y' singular."""
    assert singularize(plural) == expected_singular

@pytest.mark.parametrize(
    ("plural", "expected_singular"),
    [
        ("wolves", "wolf"),
        ("knives", "knife"),
        ("halves", "half"),
    ],
)
def test_singularize_converts_plurals_ending_in_ves(plural, expected_singular):
    """'-ves' plurals are converted, both to '-f' and '-fe' singulars."""
    assert singularize(plural) == expected_singular

@pytest.mark.parametrize(
    ("plural", "expected_singular"),
    [
        ("matrices", "matrix"),
        ("vertices", "vertex"),
        ("indices", "index"),
        ("aliases", "alias"),
        ("statuses", "status"),
        ("quizzes", "quiz"),
        ("analyses", "analysis"),
        ("crises", "crisis"),
        ("oxen", "ox"),
        ("mice", "mouse"),
        # "phenomena" is not listed as uncountable and no singular rule rewrites
        # the "-a" ending, so inflection returns it untouched (library limitation).
        ("phenomena", "phenomena"),
    ],
)
def test_singularize_converts_latin_greek_and_other_irregular_plurals(
    plural, expected_singular
):
    """Words with irregular plural endings are mapped to their singular stem."""
    assert singularize(plural) == expected_singular

@pytest.mark.parametrize(
    "word",
    [
        "sheep",
        "equipment",
        "information",
        "fish",
        "money",
        "rice",
    ],
)
def test_singularize_returns_common_uncountable_nouns_unchanged(word):
    """Uncountable nouns (no plural/singular distinction) are untouched."""
    assert singularize(word) == word

def test_singularize_strips_plural_marker_from_accented_word():
    """Non-ASCII letters are preserved while the plural suffix is removed."""
    assert singularize("cafés") == "café"

def test_singularize_returns_non_ascii_word_without_plural_marker_unchanged():
    """A non-ASCII word with no plural marker is returned as-is."""
    assert singularize("Pokémon") == "Pokémon"

def test_singularize_returns_empty_string_for_empty_input():
    """The empty string has no plural form and is returned unchanged."""
    assert singularize("") == ""

def test_singularize_always_returns_a_string(documented_examples):
    """Whatever the input, a str is handed back to the caller."""
    for word, _expected in documented_examples:
        assert isinstance(singularize(word), str)

    assert isinstance(singularize(""), str)

def test_singularize_matches_documented_examples(documented_examples):
    """Every example advertised in the docstring is honoured."""
    for word, expected_singular in documented_examples:
        assert singularize(word) == expected_singular

@pytest.mark.parametrize(
    "word", ["posts", "octopi", "sheep", "word", "CamelOctopi", "boxes", "cities"]
)
def test_singularize_is_idempotent(word):
    """Applying singularize twice is the same as applying it once."""
    once = singularize(word)
    assert singularize(once) == once

def test_singularize_reverses_pluralize(plural_round_trips):
    """singularize is the reverse operation of pluralize."""
    for singular, plural in plural_round_trips:
        assert pluralize(singular) == plural
        assert singularize(plural) == singular

def test_singularize_does_not_treat_input_as_a_regular_expression():
    """Regex metacharacters inside the input are inert and kept verbatim."""
    assert singularize("items.") == "items."

@pytest.mark.parametrize(
    "value",
    [None, 42, 3.5, b"posts", ["posts"]],
)
def test_singularize_raises_type_error_for_non_string_input(value):
    """Only str input is supported; anything else fails loudly."""
    with pytest.raises(TypeError):
        singularize(value)

def test_singularize_does_not_mutate_or_consume_its_input():
    """Strings are immutable, so repeated calls give identical results."""
    word = "posts"

    assert singularize(word) == "post"
    assert singularize(word) == "post"
    assert word == "posts"
