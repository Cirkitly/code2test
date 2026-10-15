import pytest
from inflection import pluralize, tableize, underscore

@pytest.fixture
def documented_examples():
    """Model-name/table-name pairs taken verbatim from tableize's docstring."""
    return [
        ("RawScaledScorer", "raw_scaled_scorers"),
        ("egg_and_ham", "egg_and_hams"),
        ("fancyCategory", "fancy_categories"),
    ]

@pytest.fixture
def model_names():
    """A representative sample of Rails style model class names used for property checks."""
    return [
        "RawScaledScorer",
        "FancyCategory",
        "fancyCategory",
        "egg_and_ham",
        "EggAndHam",
        "HTTPResponse",
        "Box",
    ]

def test_tableize_pascal_case_model_name_becomes_plural_snake_case_table_name():
    assert tableize("RawScaledScorer") == "raw_scaled_scorers"

@pytest.mark.parametrize(
    "model_name, expected_table_name",
    [
        ("RawScaledScorer", "raw_scaled_scorers"),
        ("egg_and_ham", "egg_and_hams"),
        ("fancyCategory", "fancy_categories"),
    ],
)
def test_tableize_reproduces_every_documented_rails_example(model_name, expected_table_name):
    assert tableize(model_name) == expected_table_name

def test_tableize_snake_case_name_pluralizes_only_the_final_word():
    assert tableize("egg_and_ham") == "egg_and_hams"

def test_tableize_does_not_pluralize_words_before_the_last_one():
    table_name = tableize("egg_and_ham")
    assert table_name.startswith("egg_and_")
    assert not table_name.startswith("eggs")

def test_tableize_lower_camel_case_name():
    assert tableize("fancyCategory") == "fancy_categories"

def test_tableize_upper_camel_case_name():
    assert tableize("FancyCategory") == "fancy_categories"

def test_tableize_multi_word_camel_case_only_pluralizes_the_trailing_word():
    assert tableize("EggAndHam") == "egg_and_hams"

def test_tableize_handles_names_containing_acronyms():
    assert tableize("HTTPResponse") == "http_responses"

def test_tableize_standalone_acronym_gets_only_a_trailing_s():
    assert tableize("HTML") == "htmls"

def test_tableize_appends_es_for_names_ending_in_sibilant_x():
    assert tableize("Box") == "boxes"

def test_tableize_appends_es_for_names_ending_in_status():
    table_name = tableize("Status")
    assert table_name.startswith("status")
    assert table_name.endswith("es")
    assert table_name != "status"

def test_tableize_turns_consonant_plus_y_into_ies():
    assert tableize("ToyCategory") == "toy_categories"

def test_tableize_y_after_a_vowel_only_gets_an_s():
    assert tableize("Toy") == "toys"

def test_tableize_leaves_uncountable_nouns_unchanged():
    assert tableize("Sheep") == "sheep"

def test_tableize_is_stable_for_an_already_plural_name():
    assert tableize("raw_scaled_scorers") == "raw_scaled_scorers"

def test_tableize_output_is_always_lowercase_snake_case(model_names):
    for model_name in model_names:
        table_name = tableize(model_name)
        assert isinstance(table_name, str)
        assert table_name == table_name.lower()
        assert " " not in table_name

def test_tableize_is_the_plural_of_the_underscored_name(documented_examples):
    for model_name, expected_table_name in documented_examples:
        assert tableize(model_name) == pluralize(underscore(model_name))
        assert tableize(model_name) == expected_table_name

def test_tableize_preserves_unicode_letters_while_pluralizing():
    table_name = tableize("Café")
    assert isinstance(table_name, str)
    assert table_name.startswith("caf")
    assert table_name.endswith("s")

def test_tableize_empty_string_returns_empty_string():
    assert tableize("") == ""

def test_tableize_raises_type_error_for_none():
    with pytest.raises(TypeError):
        tableize(None)

def test_tableize_raises_type_error_for_integer_input():
    with pytest.raises(TypeError):
        tableize(1)

def test_tableize_raises_type_error_for_bytes_input():
    with pytest.raises(TypeError):
        tableize(b"RawScaledScorer")
