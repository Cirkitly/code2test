import pytest
from inflection import _irregular
from inflection import PLURALS, SINGULARS, pluralize, singularize

@pytest.fixture(autouse=True)
def restore_inflection_rule_lists():
    """Restore the global PLURALS/SINGULARS rule lists so tests do not leak state.

    ``_irregular`` mutates module-level state, so the original lists are
    snapshotted and restored afterwards to keep tests independent.
    """
    saved_plurals = list(PLURALS)
    saved_singulars = list(SINGULARS)
    yield
    PLURALS[:] = saved_plurals
    SINGULARS[:] = saved_singulars

import pytest

from inflection import _irregular
from inflection import PLURALS, SINGULARS, pluralize, singularize


@pytest.fixture(autouse=True)
def restore_inflection_rule_lists():
    """Restore the global PLURALS/SINGULARS rule lists so tests do not leak state."""
    saved_plurals = list(PLURALS)
    saved_singulars = list(SINGULARS)
    yield
    PLURALS[:] = saved_plurals
    SINGULARS[:] = saved_singulars


def test_irregular_registers_plural_and_singular_rules_for_matching_first_letters():
    """The happy path: a matching-first-letter pair teaches both directions.

    Because the words start with the same letter, case-insensitive rules are
    registered, so ``pluralize``/``singularize`` work for any capitalisation and
    keep the case of the first letter of the input.
    """
    assert _irregular("person", "people") is None

    assert pluralize("person") == "people"
    assert pluralize("Person") == "People"
    assert singularize("people") == "person"
    assert singularize("People") == "Person"


def test_irregular_adds_two_plural_rules_and_one_singular_rule_at_the_front():
    """Matching first letters insert 2 PLURALS rules and 1 SINGULARS rule at index 0.

    The rules are inserted with ``insert(0, ...)``, so the new rules take
    priority over every rule registered before them (including the built-ins).
    """
    plurals_before = list(PLURALS)
    singulars_before = list(SINGULARS)

    _irregular("person", "people")

    assert len(PLURALS) == len(plurals_before) + 2
    assert len(SINGULARS) == len(singulars_before) + 1
    assert PLURALS[0] == (r"(?i)(p)eople$", r"\1eople")
    assert PLURALS[1] == (r"(?i)(p)erson$", r"\1eople")
    assert SINGULARS[0] == (r"(?i)(p)eople$", r"\1erson")


def test_irregular_keeps_the_plural_of_an_already_plural_word_unchanged():
    """A plural->plural rule is registered so an irregular plural is not double-pluralized."""
    _irregular("person", "people")

    assert pluralize("people") == "people"


def test_irregular_rules_take_priority_over_the_built_in_rules():
    """Rules registered by _irregular are inserted at the front, beating the built-ins."""
    baseline = pluralize("person")
    assert baseline != "people"

    _irregular("person", "people")

    assert pluralize("person") == "people"


def test_irregular_registers_rules_in_front_of_previously_registered_ones():
    """A later registration overrides an earlier one for the same word."""
    _irregular("child", "children")
    assert pluralize("child") == "children"

    _irregular("child", "kids")

    assert pluralize("child") == "kids"


def test_irregular_uses_the_case_insensitive_branch_when_first_letters_differ_only_in_case():
    """First letters are compared case-insensitively, so 'Apple'/'apples' uses the matching branch."""
    plurals_before = len(PLURALS)
    singulars_before = len(SINGULARS)

    _irregular("Apple", "apples")

    assert len(PLURALS) == plurals_before + 2
    assert len(SINGULARS) == singulars_before + 1
    assert pluralize("apple") == "apples"
    assert pluralize("Apple") == "Apples"
    assert singularize("apples") == "apple"


def test_irregular_with_different_first_letters_builds_case_sensitive_rules():
    """Different first letters produce 4 PLURALS rules and 2 SINGULARS rules.

    Each rule pins the first letter of both the singular and the plural (upper
    and lower case) while the remaining characters are matched
    case-insensitively via character classes.
    """
    plurals_before = len(PLURALS)
    singulars_before = len(SINGULARS)

    _irregular("child", "kids")

    assert len(PLURALS) == plurals_before + 4
    assert len(SINGULARS) == singulars_before + 2
    assert PLURALS[0] == ("k[iI][dD][sS]$", "kids")
    assert PLURALS[1] == ("K[iI][dD][sS]$", "Kids")
    assert PLURALS[2] == ("c[hH][iI][lL][dD]$", "kids")
    assert PLURALS[3] == ("C[hH][iI][lL][dD]$", "Kids")
    assert SINGULARS[0] == ("k[iI][dD][sS]$", "child")
    assert SINGULARS[1] == ("K[iI][dD][sS]$", "Child")


def test_irregular_with_different_first_letters_maps_both_directions():
    """With different first letters, pluralize and singularize still work for both forms."""
    _irregular("child", "kids")

    assert pluralize("child") == "kids"
    assert pluralize("Child") == "Kids"
    assert pluralize("kids") == "kids"
    assert pluralize("Kids") == "Kids"
    assert singularize("kids") == "child"
    assert singularize("Kids") == "Child"


def test_irregular_different_first_letter_rules_ignore_the_case_of_inner_letters():
    """Inner characters are matched case-insensitively (character classes)."""
    _irregular("child", "kids")

    assert pluralize("cHiLd") == "kids"


def test_irregular_handles_single_character_words():
    """Edge case: words of length one produce rules with an empty tail."""
    _irregular("x", "y")

    assert pluralize("x") == "y"
    assert pluralize("X") == "Y"
    assert pluralize("y") == "y"
    assert singularize("y") == "x"
    assert singularize("Y") == "X"


def test_irregular_supports_words_that_are_the_same_in_singular_and_plural():
    """Edge case: a word that does not change form stays unchanged both ways."""
    _irregular("sheep", "sheep")

    assert pluralize("sheep") == "sheep"
    assert pluralize("Sheep") == "Sheep"
    assert singularize("sheep") == "sheep"


def test_irregular_preserves_the_case_of_the_first_letter():
    """The replacement reuses the captured first letter, keeping the input casing."""
    _irregular("ox", "oxen")

    assert pluralize("ox") == "oxen"
    assert pluralize("Ox") == "Oxen"
    assert singularize("oxen") == "ox"
    assert singularize("Oxen") == "Ox"


def test_irregular_handles_non_ascii_words():
    """The inline (?i) flag applies to non-ASCII letters as well."""
    _irregular("café", "cafés")

    assert pluralize("café") == "cafés"
    assert pluralize("Café") == "Cafés"
    assert singularize("cafés") == "café"
    assert singularize("Cafés") == "Café"


def test_irregular_uses_the_word_as_a_raw_regular_expression():
    """The word is interpolated into the pattern verbatim (no re.escaping)."""
    _irregular("a.b", "a.bc")

    # '.' acts as a wildcard, so "axbc" matches the registered "a.bc" rule.
    assert pluralize("axbc") == "abc"
    assert pluralize("a.b") == "a.bc"


def test_irregular_raises_index_error_for_an_empty_singular_word():
    """Negative case: an empty singular has no first character to inspect."""
    plurals_before = len(PLURALS)
    singulars_before = len(SINGULARS)

    with pytest.raises(IndexError):
        _irregular("", "people")

    assert len(PLURALS) == plurals_before
    assert len(SINGULARS) == singulars_before


def test_irregular_raises_index_error_for_an_empty_plural_word():
    """Negative case: an empty plural has no first character to inspect."""
    plurals_before = len(PLURALS)
    singulars_before = len(SINGULARS)

    with pytest.raises(IndexError):
        _irregular("person", "")

    assert len(PLURALS) == plurals_before
    assert len(SINGULARS) == singulars_before


@pytest.mark.parametrize(
    "singular, plural",
    [(None, "people"), ("person", None)],
)
def test_irregular_raises_type_error_for_non_string_words(singular, plural):
    """Negative case: the arguments are subscripted, so non-strings blow up."""
    with pytest.raises(TypeError):
        _irregular(singular, plural)

from inflection import _irregular
from inflection import PLURALS, SINGULARS


def test_irregular_adds_two_plural_rules_and_one_singular_rule_at_the_front():
    plurals_before = list(PLURALS)
    singulars_before = list(SINGULARS)

    _irregular("person", "people")

    assert len(PLURALS) == len(plurals_before) + 2
    assert len(SINGULARS) == len(singulars_before) + 1
    assert PLURALS[0] == (r"(?i)(p)eople$", r"\1eople")
    assert PLURALS[1] == (r"(?i)(p)erson$", r"\1eople")
    assert SINGULARS[0] == (r"(?i)(p)eople$", r"\1erson")

from inflection import _irregular
from inflection import pluralize


def test_irregular_keeps_the_plural_of_an_already_plural_word_unchanged():
    _irregular("person", "people")

    assert pluralize("people") == "people"

def test_irregular_rules_take_priority_over_the_built_in_rules():
    """Rules registered by _irregular are inserted at the front, beating the built-ins.

    ``pluralize("person")`` already returns ``"people"`` thanks to the rules
    that ship with the library. Registering a *different* irregular pair for the
    same word therefore demonstrates that the freshly added rules are consulted
    before the pre-existing ones.
    """
    # Pre-existing (built-in) behaviour
    assert pluralize("person") == "people"

    _irregular("person", "persons")

    # The newly registered rules win over the pre-existing ones
    assert pluralize("person") == "persons"
    assert pluralize("Person") == "Persons"
    assert singularize("persons") == "person"
    assert singularize("Persons") == "Person"

from inflection import _irregular
from inflection import pluralize


def test_irregular_registers_rules_in_front_of_previously_registered_ones():
    _irregular("child", "children")
    assert pluralize("child") == "children"

    _irregular("child", "kids")

    assert pluralize("child") == "kids"

from inflection import _irregular
from inflection import PLURALS, SINGULARS, pluralize, singularize


def test_irregular_uses_the_case_insensitive_branch_when_first_letters_differ_only_in_case():
    plurals_before = len(PLURALS)
    singulars_before = len(SINGULARS)

    _irregular("Apple", "apples")

    assert len(PLURALS) == plurals_before + 2
    assert len(SINGULARS) == singulars_before + 1
    assert pluralize("apple") == "apples"
    assert pluralize("Apple") == "Apples"
    assert singularize("apples") == "apple"

from inflection import _irregular
from inflection import PLURALS, SINGULARS


def test_irregular_with_different_first_letters_builds_case_sensitive_rules():
    plurals_before = len(PLURALS)
    singulars_before = len(SINGULARS)

    _irregular("child", "kids")

    assert len(PLURALS) == plurals_before + 4
    assert len(SINGULARS) == singulars_before + 2
    assert PLURALS[0] == ("k[iI][dD][sS]$", "kids")
    assert PLURALS[1] == ("K[iI][dD][sS]$", "Kids")
    assert PLURALS[2] == ("c[hH][iI][lL][dD]$", "kids")
    assert PLURALS[3] == ("C[hH][iI][lL][dD]$", "Kids")
    assert SINGULARS[0] == ("k[iI][dD][sS]$", "child")
    assert SINGULARS[1] == ("K[iI][dD][sS]$", "Child")

from inflection import _irregular
from inflection import pluralize, singularize


def test_irregular_with_different_first_letters_maps_both_directions():
    _irregular("child", "kids")

    assert pluralize("child") == "kids"
    assert pluralize("Child") == "Kids"
    assert pluralize("kids") == "kids"
    assert pluralize("Kids") == "Kids"
    assert singularize("kids") == "child"
    assert singularize("Kids") == "Child"

from inflection import _irregular
from inflection import pluralize


def test_irregular_different_first_letter_rules_ignore_the_case_of_inner_letters():
    _irregular("child", "kids")

    assert pluralize("cHiLd") == "kids"

from inflection import _irregular
from inflection import pluralize, singularize


def test_irregular_handles_single_character_words():
    _irregular("x", "y")

    assert pluralize("x") == "y"
    assert pluralize("X") == "Y"
    assert pluralize("y") == "y"
    assert singularize("y") == "x"
    assert singularize("Y") == "X"

from inflection import _irregular
from inflection import pluralize, singularize


def test_irregular_supports_words_that_are_the_same_in_singular_and_plural():
    _irregular("sheep", "sheep")

    assert pluralize("sheep") == "sheep"
    assert pluralize("Sheep") == "Sheep"
    assert singularize("sheep") == "sheep"

from inflection import _irregular
from inflection import pluralize, singularize


def test_irregular_preserves_the_case_of_the_first_letter():
    _irregular("ox", "oxen")

    assert pluralize("ox") == "oxen"
    assert pluralize("Ox") == "Oxen"
    assert singularize("oxen") == "ox"
    assert singularize("Oxen") == "Ox"

from inflection import _irregular
from inflection import pluralize, singularize


def test_irregular_handles_non_ascii_words():
    _irregular("café", "cafés")

    assert pluralize("café") == "cafés"
    assert pluralize("Café") == "Cafés"
    assert singularize("cafés") == "café"
    assert singularize("Cafés") == "Café"

def test_irregular_uses_the_word_as_a_raw_regular_expression():
    """The word is interpolated into the pattern verbatim (no re.escaping).

    The ``.`` therefore behaves as a wildcard while matching (``"axbc"`` matches
    the registered ``a.bc`` rule), while the replacement keeps the literal dot
    that is part of ``plural[1:]``.
    """
    _irregular("a.b", "a.bc")

    # '.' in the pattern acts as a wildcard: 'x' is matched by '.',
    # and the replacement re-inserts the literal '.' from plural[1:].
    assert pluralize("axbc") == "a.bc"
    # The literal form matches too.
    assert pluralize("a.b") == "a.bc"
    # Same story for the singular direction.
    assert singularize("axbc") == "a.b"

import pytest

from inflection import _irregular
from inflection import PLURALS, SINGULARS


def test_irregular_raises_index_error_for_an_empty_singular_word():
    plurals_before = len(PLURALS)
    singulars_before = len(SINGULARS)

    with pytest.raises(IndexError):
        _irregular("", "people")

    assert len(PLURALS) == plurals_before
    assert len(SINGULARS) == singulars_before

import pytest

from inflection import _irregular
from inflection import PLURALS, SINGULARS


def test_irregular_raises_index_error_for_an_empty_plural_word():
    plurals_before = len(PLURALS)
    singulars_before = len(SINGULARS)

    with pytest.raises(IndexError):
        _irregular("person", "")

    assert len(PLURALS) == plurals_before
    assert len(SINGULARS) == singulars_before

import pytest

from inflection import _irregular


@pytest.mark.parametrize(
    "singular, plural",
    [(None, "people"), ("person", None)],
)
def test_irregular_raises_type_error_for_non_string_words(singular, plural):
    with pytest.raises(TypeError):
        _irregular(singular, plural)
