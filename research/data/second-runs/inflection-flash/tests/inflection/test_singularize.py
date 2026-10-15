import pytest
from inflection import pluralize
from inflection import singularize

@pytest.fixture(scope="module")
def documented_examples():
    """(input, expected output) pairs taken from the function's own docstring."""
    return [
        ("posts", "post"),
        ("octopi", "octopus"),
        ("sheep", "sheep"),
        ("word", "word"),
        ("CamelOctopi", "CamelOctopus"),
    ]

@pytest.fixture(scope="module")
def uncountable_words():
    """Words without a distinct plural form; they must be returned unchanged.

    This mirrors the module's ``UNCOUNTABLES`` table: when a word matches one of
    its entries as a whole (trailing) word, ``singularize`` returns it verbatim
    before any ``SINGULARS`` rule is applied.

    Note: words that are uncountable in English but absent from the module's
    table (e.g. "police") are *not* short-circuited and are therefore not listed
    here as protected words.
    """
    return [
        "equipment", "information", "rice", "money", "species",
        "series", "fish", "sheep", "jeans",
    ]

@pytest.fixture(scope="module")
def singular_words():
    """Words that are already singular and must be returned unchanged.

    Words whose singular form merely looks like a plural (e.g. "bus"/"buses",
    "status"/"statuses", "alias"/"aliases") are covered by the (plural, singular)
    pair fixtures instead of this one.
    """
    return [
        "post", "word", "octopus", "virus", "box", "quiz",
        "city", "baby", "mouse", "knife", "wife", "life", "half",
        "hive", "motive", "movie", "tomato", "hero", "analysis",
        "matrix", "medium", "church", "shoe", "match", "wolf",
        "shelf", "money", "sheep", "series",
    ]

@pytest.fixture(scope="module")
def round_trip_words():
    """Singular words whose pluralised form must singularise back to the original."""
    return [
        "post", "word", "octopus", "virus", "ox", "box", "quiz",
        "tomato", "mouse", "knife", "wife", "life", "half", "hive",
        "motive", "movie", "analysis", "medium", "city", "baby",
        "church", "shoe", "status", "bus", "matrix", "match",
    ]

@pytest.fixture(scope="module")
def regular_plurals():
    """(plural, singular) pairs produced by the common "-s"/"-es" rules."""
    return [
        ("posts", "post"),
        ("words", "word"),
        ("searches", "search"),
        ("switches", "switch"),
        ("boxes", "box"),
        ("churches", "church"),
        ("dishes", "dish"),
        ("glasses", "glass"),
        ("watches", "watch"),
        ("cities", "city"),
        ("babies", "baby"),
        ("queries", "query"),
        ("shelves", "shelf"),
        ("knives", "knife"),
        ("lives", "life"),
        ("wives", "wife"),
        ("hives", "hive"),
        ("potatoes", "potato"),
        ("tomatoes", "tomato"),
        ("shoes", "shoe"),
        ("buses", "bus"),
        ("movies", "movie"),
        ("databases", "database"),
    ]

@pytest.fixture(scope="module")
def irregular_plurals():
    """(plural, singular) pairs produced by the irregular rules.

    ``inflection`` is a rule table, not a dictionary: only the ``matr|vert|ind``
    "-ices" family is special-cased, so any other "-ices" word falls through to
    the generic "drop a trailing s" rule (see the last entry).
    """
    return [
        ("mice", "mouse"),
        ("lice", "louse"),
        ("oxen", "ox"),
        ("matrices", "matrix"),
        ("vertices", "vertex"),
        ("indices", "index"),
        ("octopi", "octopus"),
        ("viri", "virus"),
        ("quizzes", "quiz"),
        ("analyses", "analysis"),
        ("crises", "crisis"),
        ("theses", "thesis"),
        ("bases", "basis"),
        ("diagnoses", "diagnosis"),
        ("parentheses", "parenthesis"),
        ("prognoses", "prognosis"),
        ("synopses", "synopsis"),
        ("media", "medium"),
        ("buffaloes", "buffalo"),
        ("statuses", "status"),
        ("aliases", "alias"),
        ("apices", "apice"),
    ]

def test_singularize_returns_documented_singular_forms(documented_examples):
    """Every documented example must produce exactly the documented singular form."""
    for word, expected in documented_examples:
        assert singularize(word) == expected, "unexpected result for %r" % (word,)

def test_singularize_always_returns_a_string(documented_examples):
    """The public contract is a str-in/str-out transformation."""
    for word, _expected in documented_examples:
        assert isinstance(singularize(word), str)

def test_singularize_converts_regular_plural_endings(regular_plurals):
    """Common '-s' and '-es' plurals are reduced to their singular stem."""
    for plural, expected in regular_plurals:
        assert singularize(plural) == expected, "unexpected singular for %r" % (plural,)

def test_singularize_converts_irregular_plurals(irregular_plurals):
    """Irregular plurals (-i, -ice, -es, -ices, -ves, -en) map back to their singular."""
    for plural, expected in irregular_plurals:
        assert singularize(plural) == expected, "unexpected singular for %r" % (plural,)

def test_singularize_is_the_reverse_of_pluralize(round_trip_words):
    """The documented intent is 'the reverse of pluralize': pluralize then singularize is a no-op."""
    for word in round_trip_words:
        plural = pluralize(word)
        assert singularize(plural) == word, "round trip failed for %r -> %r" % (word, plural)

def test_singularize_returns_uncountable_words_unchanged(uncountable_words):
    """Uncountables are detected first and returned verbatim, never 'singularised'."""
    for word in uncountable_words:
        assert singularize(word) == word, "unexpected singular for %r" % (word,)

def test_singularize_matches_uncountables_case_insensitively():
    """The uncountable check is case-insensitive but preserves the original casing."""
    assert singularize("Sheep") == "Sheep"
    assert singularize("MONEY") == "MONEY"
    assert singularize("FISH") == "FISH"

def test_singularize_only_treats_trailing_uncountables_as_uncountable():
    """The uncountable check is anchored at the end of the word.

    An exact/trailing uncountable short-circuits the rule table, but a longer word
    that merely *starts* with an uncountable is regularised like any other word.
    """
    assert singularize("sheep") == "sheep"  # exact uncountable -> verbatim
    assert singularize("money") == "money"  # exact uncountable -> verbatim
    assert singularize("sheepdog") == "sheepdog"  # no rule matches, left alone
    assert singularize("fishstick") == "fishstick"  # no rule matches, left alone
    assert singularize("moneybags") == "moneybag"  # regular "-s" rule applies

def test_singularize_leaves_already_singular_words_unchanged(singular_words):
    """Words that are already singular (including words ending in 's') are returned as-is."""
    for word in singular_words:
        assert singularize(word) == word, "already singular word %r was modified" % (word,)

def test_singularize_is_idempotent(round_trip_words):
    """Applying singularize twice must not change the result any further."""
    for word in round_trip_words:
        once = singularize(word)
        assert singularize(once) == once, "not idempotent for %r" % (word,)

def test_singularize_never_returns_a_longer_string(round_trip_words, uncountable_words):
    """Singularising only ever strips a suffix, so the result is never longer than the input."""
    for word in list(round_trip_words) + list(uncountable_words):
        result = singularize(word)
        assert len(result) <= len(word), (
            "singularize(%r) returned %r, which is longer than the input" % (word, result)
        )

def test_singularize_returns_empty_string_for_empty_word():
    """An empty word is a valid input and is returned unchanged (no exception)."""
    assert singularize("") == ""

def test_singularize_keeps_words_that_already_end_with_s():
    """A final 's' is kept whenever a dedicated rule or the uncountable list covers the word."""
    for word in ["octopus", "virus", "analysis", "series", "species", "jeans"]:
        assert singularize(word) == word, "final 's' was stripped from %r" % (word,)

def test_singularize_is_case_insensitive():
    """Matching of plural endings ignores case while keeping the original casing of the word."""
    assert singularize("POSTS") == "POST"
    assert singularize("Octopi") == "Octopus"
    assert singularize("CamelOctopi") == "CamelOctopus"

def test_singularize_does_not_touch_words_ending_in_punctuation():
    """Plural endings are matched at the end of the string, so trailing punctuation blocks them."""
    assert singularize("posts!") == "posts!"
    assert singularize("posts.") == "posts."
    assert singularize("posts?") == "posts?"

def test_singularize_preserves_surrounding_whitespace():
    """Whitespace is never inserted or removed; padding after the word blocks the ending rules."""
    assert singularize(" posts ") == " posts "
    assert singularize("posts ") == "posts "
    assert singularize(" posts") == " post"

def test_singularize_handles_non_ascii_letters():
    """Non-ASCII letters are supported; only the trailing 's' of a plural is removed."""
    assert singularize("cafés") == "café"

def test_singularize_raises_type_error_for_none():
    """Passing None (a non-str) raises TypeError from the regex engine."""
    with pytest.raises(TypeError):
        singularize(None)

def test_singularize_raises_type_error_for_integer():
    """Passing an int (a non-str) raises TypeError from the regex engine."""
    with pytest.raises(TypeError):
        singularize(123)

def test_singularize_raises_type_error_for_bytes():
    """Bytes are not accepted: a str pattern cannot be applied to a bytes object."""
    with pytest.raises(TypeError):
        singularize(b"posts")
