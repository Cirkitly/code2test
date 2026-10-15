import pytest
from inflection import _irregular
import inflection

@pytest.fixture
def irregular_registry():
    """Provide a snapshot/restore fixture around the module-level PLURALS and SINGULARS
    rule lists, plus thin wrappers exposing the public pluralize/singularize API so that
    tests can observe the effect of _irregular without polluting other tests.
    """
    import inflection

    saved_plurals = list(inflection.PLURALS)
    saved_singulars = list(inflection.SINGULARS)

    class Registry:
        def __init__(self):
            self.plurals = inflection.PLURALS
            self.singulars = inflection.SINGULARS

        def irregular(self, singular, plural):
            return inflection._irregular(singular, plural)

        def pluralize(self, word):
            return inflection.pluralize(word)

        def singularize(self, word):
            return inflection.singularize(word)

    try:
        yield Registry()
    finally:
        inflection.PLURALS[:] = saved_plurals
        inflection.SINGULARS[:] = saved_singulars

def test_irregular_same_initial_letter_pluralize(irregular_registry):
    irregular_registry.irregular('person', 'people')

    assert irregular_registry.pluralize('person') == 'people'
