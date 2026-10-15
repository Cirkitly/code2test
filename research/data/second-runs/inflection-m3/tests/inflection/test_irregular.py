import pytest
from inflection import _irregular, pluralize, singularize

def test_irregular_returns_none():
    """The function returns None as it only modifies global state."""
    result = _irregular('person', 'people')
    assert result is None


def test_irregular_pluralize_with_same_first_letter():
    """Same-first-letter path: pluralize applies the newly registered rule.

    The source prepends rules:
      - (?i)(p)eople$  -> \\1eople
      - (?i)(p)erson$  -> \\1eople
    so pluralize('person') matches the second rule and returns 'people'.
    """
    _irregular('person', 'people')
    assert pluralize('person') == 'people'


def test_irregular_singularize_with_same_first_letter():
    """Same-first-letter path: singularize applies the newly registered rule.

    The source prepends a SINGULARS rule:
      - (?i)(p)eople$  -> \\1erson
    so singularize('people') returns 'person'.
    """
    _irregular('person', 'people')
    assert singularize('people') == 'person'


def test_irregular_first_letter_case_preserved_in_pluralize():
    """The capture group \\1 keeps the first letter's case in the output.

    Pattern: (?i)(c)hild$  -> \\1hildren
    For input 'Child', \\1 captures 'C' and plural[1:] is 'hildren',
    so the result is 'Children' (first letter upper, rest as in source).
    """
    _irregular('child', 'children')
    assert pluralize('Child') == 'Children'


def test_irregular_first_letter_case_preserved_in_singularize():
    """The capture group \\1 keeps the first letter's case when singularizing.

    Pattern: (?i)(c)hildren$  -> \\1hild
    For input 'Children', \\1 captures 'C' and singular[1:] is 'hild',
    so the result is 'Child'.
    """
    _irregular('child', 'children')
    assert singularize('Children') == 'Child'


def test_irregular_different_first_letter_pluralize():
    """Different-first-letter path: the else branch fires.

    For ('ox', 'axen'), 'O' != 'A' triggers the else branch, producing:
      - o[xX]$ -> axen
      - O[xX]$ -> AXEN
      - a[xX][eE][nN]$ -> axen
      - A[xX][eE][nN]$ -> AXEN
    pluralize('ox') matches the o[xX]$ rule and returns 'axen'.
    """
    _irregular('ox', 'axen')
    assert pluralize('ox') == 'axen'


def test_irregular_different_first_letter_singularize():
    """Different-first-letter path: SINGULARS rules work for lowercase input.

    For ('ox', 'axen'), the else branch prepends to SINGULARS:
      - a[xX][eE][nN]$ -> ox
      - A[xX][eE][nN]$ -> OX
    singularize('axen') matches the lowercase rule and returns 'ox'.
    """
    _irregular('ox', 'axen')
    assert singularize('axen') == 'ox'


def test_irregular_different_first_letter_capital_preservation():
    """Different-first-letter path: uppercase first letter selects uppercase rule.

    For input 'Ox' (capital O), the lowercase o[xX]$ rule does not match
    and the uppercase O[xX]$ rule does, producing 'Axen' (only the first
    letter of the replacement is uppercased).
    Similarly for singularize('Axen') which selects the uppercase
    replacement 'Ox'.
    """
    _irregular('ox', 'axen')
    assert pluralize('Ox') == 'Axen'
    assert singularize('Axen') == 'Ox'

def test_irregular_empty_singular_raises_index_error():
    """An empty singular string causes IndexError on singular[0] access.

    The source has no guard for empty inputs and immediately evaluates
    singular[0].upper(), so passing '' raises IndexError.
    """
    with pytest.raises(IndexError):
        _irregular('', 'people')


def test_irregular_empty_plural_raises_index_error():
    """An empty plural string causes IndexError on plural[0] access.

    The source has no guard for empty inputs and immediately evaluates
    plural[0].upper(), so passing '' raises IndexError.
    """
    with pytest.raises(IndexError):
        _irregular('person', '')


def test_irregular_multiple_registrations_compose():
    """Multiple _irregular calls all remain active.

    The function inserts new rules at index 0 of PLURALS and SINGULARS,
    so previously registered rules are not removed. Verifying both pairs
    in a single test demonstrates the prepend semantics.
    """
    _irregular('person', 'people')
    _irregular('child', 'children')
    assert pluralize('person') == 'people'
    assert pluralize('child') == 'children'
    assert singularize('people') == 'person'
    assert singularize('children') == 'child'

