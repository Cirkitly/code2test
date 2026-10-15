import pytest
from inflection import _irregular, pluralize, singularize
import inflection

@pytest.fixture
def restore_irregular_state():
    """Snapshot PLURALS/SINGULARS before the test, restore them after.

    _irregular mutates module-level globals in the inflection package; without
    isolation, later tests would inherit rules added by earlier ones.
    Using in-place slice assignment ([:] = ...) preserves the same list object
    that pluralize / singularize reference.
    """
    saved_plurals = list(inflection.PLURALS)
    saved_singulars = list(inflection.SINGULARS)
    yield
    inflection.PLURALS[:] = saved_plurals
    inflection.SINGULARS[:] = saved_singulars

def test_irregular_returns_none(restore_irregular_state):
    """_irregular is a side-effect function that returns None after registering rules."""
    assert _irregular("person", "people") is None

def test_irregular_same_first_letter_grows_plurals_by_two(restore_irregular_state):
    """When singular[0].upper() == plural[0].upper(), PLURALS gains 2 rules."""
    initial = len(inflection.PLURALS)
    _irregular("person", "people")
    assert len(inflection.PLURALS) == initial + 2

def test_irregular_same_first_letter_grows_singulars_by_one(restore_irregular_state):
    """When singular[0].upper() == plural[0].upper(), SINGULARS gains 1 rule."""
    initial = len(inflection.SINGULARS)
    _irregular("person", "people")
    assert len(inflection.SINGULARS) == initial + 1

def test_irregular_different_first_letter_grows_plurals_by_four(restore_irregular_state):
    """When singular[0].upper() != plural[0].upper(), PLURALS gains 4 rules."""
    initial = len(inflection.PLURALS)
    _irregular("is", "are")
    assert len(inflection.PLURALS) == initial + 4

def test_irregular_different_first_letter_grows_singulars_by_two(restore_irregular_state):
    """When singular[0].upper() != plural[0].upper(), SINGULARS gains 2 rules."""
    initial = len(inflection.SINGULARS)
    _irregular("is", "are")
    assert len(inflection.SINGULARS) == initial + 2

def test_irregular_inserts_new_plurals_rules_at_front(restore_irregular_state):
    """New rules are placed at the front of PLURALS so they take priority."""
    _irregular("person", "people")
    front_two_patterns = [rule[0] for rule in inflection.PLURALS[:2]]
    # One of the front rules targets the plural "people" (contains 'eople')
    assert any("eople" in p for p in front_two_patterns), (
        "Expected a plural pattern at front, got: %r" % front_two_patterns
    )
    # The other targets the singular "person" (contains 'erson')
    assert any("erson" in p for p in front_two_patterns), (
        "Expected a singular pattern at front, got: %r" % front_two_patterns
    )

def test_irregular_inserts_new_singulars_rule_at_front(restore_irregular_state):
    """New SINGULARS rule is placed at the front of SINGULARS."""
    _irregular("person", "people")
    first_singulars_pattern = inflection.SINGULARS[0][0]
    # The rule matches the plural form and replaces with the singular.
    assert "eople" in first_singulars_pattern

def test_irregular_same_first_letter_pluralize_singular_to_plural(restore_irregular_state):
    """pluralize correctly maps the registered singular to its plural form."""
    _irregular("person", "people")
    assert pluralize("person") == "people"

def test_irregular_same_first_letter_singularize_plural_to_singular(restore_irregular_state):
    """singularize correctly maps the registered plural back to its singular form."""
    _irregular("person", "people")
    assert singularize("people") == "person"

def test_irregular_same_first_letter_pluralize_is_idempotent(restore_irregular_state):
    """Pluralizing an already-plural irregular leaves the word unchanged."""
    _irregular("person", "people")
    assert pluralize("people") == "people"

def test_irregular_same_first_letter_pluralize_works_capitalized(restore_irregular_state):
    """Capitalized singular pluralizes to capitalized plural via the irregular rule."""
    _irregular("person", "people")
    # (?i) flag + capture group on first letter preserves the case of the input.
    assert pluralize("Person") == "People"

def test_irregular_same_first_letter_singularize_works_capitalized(restore_irregular_state):
    """Capitalized plural singularizes to capitalized singular via the irregular rule."""
    _irregular("person", "people")
    assert singularize("People") == "Person"

def test_irregular_different_first_letter_pluralize(restore_irregular_state):
    """The else branch still correctly pluralizes the registered irregular."""
    _irregular("is", "are")
    assert pluralize("is") == "are"

def test_irregular_different_first_letter_singularize(restore_irregular_state):
    """The else branch still correctly singularizes the registered irregular."""
    _irregular("is", "are")
    assert singularize("are") == "is"

def test_irregular_does_not_break_unrelated_pluralization(restore_irregular_state):
    """Adding an irregular rule leaves unrelated words' pluralization intact."""
    _irregular("person", "people")
    # "child" must not be turned into "people" by the new rule.
    result = pluralize("child")
    assert "people" not in result.lower()
    assert "child" in result.lower()

def test_irregular_multiple_registrations_all_work(restore_irregular_state):
    """Multiple _irregular calls register independent, working rules."""
    _irregular("person", "people")
    _irregular("mouse", "mice")
    assert pluralize("person") == "people"
    assert pluralize("mouse") == "mice"
    assert singularize("people") == "person"
    assert singularize("mice") == "mouse"

def test_irregular_called_twice_with_same_args_adds_rules_each_call(restore_irregular_state):
    """Repeated calls with identical args stack additional rules at index 0."""
    plurals_before = len(inflection.PLURALS)
    singulars_before = len(inflection.SINGULARS)
    _irregular("person", "people")
    _irregular("person", "people")
    # 2 PLURALS inserts per call, 1 SINGULARS insert per call.
    assert len(inflection.PLURALS) == plurals_before + 4
    assert len(inflection.SINGULARS) == singulars_before + 2

def test_irregular_same_first_letter_patterns_are_case_insensitive(restore_irregular_state):
    """The newly inserted PLURALS patterns carry the (?i) flag for case-insensitivity."""
    _irregular("person", "people")
    patterns = [rule[0] for rule in inflection.PLURALS[:2]]
    assert all("(?i)" in p for p in patterns), (
        "Expected case-insensitive flag in all front patterns: %r" % patterns
    )

def test_irregular_same_first_letter_uses_first_letter_capture_group(restore_irregular_state):
    """The same-first-letter pattern captures the first letter so case is preserved on substitution."""
    _irregular("person", "people")
    pattern = inflection.PLURALS[1][0]  # the singular -> plural rule
    # Pattern structure: r"(?i)({}){}$".format(singular[0], singular[1:])
    # => r"(?i)(p)erson$"  -- a literal "r" in pattern proves "(p)" capture group.
    assert "(p)" in pattern
