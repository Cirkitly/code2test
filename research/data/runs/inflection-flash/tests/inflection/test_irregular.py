import re
import pytest
import inflection
from inflection import _irregular
from inflection import PLURALS
from inflection import SINGULARS

def _snapshot():
    """Capture the current contents of the rule tables and their ordering."""
    return (list(PLURALS), list(SINGULARS))


def _restore(snapshot):
    """Reset the rule tables back to a previously captured state."""
    PLURALS[:], SINGULARS[:] = snapshot


@pytest.fixture(autouse=True)
def isolated_rule_tables():
    """Give every test a private, restorable copy of the global rule tables.

    _irregular mutates the module level PLURALS/SINGULARS lists in place, so
    tests restore them afterwards to avoid leaking state into other tests.
    """
    saved = _snapshot()
    yield
    _restore(saved)

def test_irregular_same_first_letter_inserts_three_rules_total():
    """'person'/'people' share the leading 'p', so the simple branch runs.

    That branch inserts 2 rules into PLURALS and 1 rule into SINGULARS.
    """
    plural_before = len(PLURALS)
    singular_before = len(SINGULARS)

    result = _irregular('person', 'people')

    assert result is None, "_irregular returns None; it works by side effect"
    assert len(PLURALS) == plural_before + 2
    assert len(SINGULARS) == singular_before + 1
