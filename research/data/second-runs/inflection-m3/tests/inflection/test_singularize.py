import pytest
from inflection import singularize
from inflection import pluralize

def test_singularize_documented_posts_to_post():
    """Primary happy path: a regular plural ending in 's' should be singularized."""
    assert singularize("posts") == "post"

def test_singularize_documented_octopi_to_octopus():
    """Documented example: 'octopi' becomes 'octopus' via the ([octop|vir])i$ rule."""
    assert singularize("octopi") == "octopus"

def test_singularize_documented_sheep_unchanged():
    """Documented example: uncountable 'sheep' is returned unchanged."""
    assert singularize("sheep") == "sheep"

def test_singularize_documented_word_unchanged():
    """Documented example: already-singular 'word' is returned unchanged."""
    assert singularize("word") == "word"

def test_singularize_documented_camel_octopi_to_camel_octopus():
    """Documented example: CamelCase 'CamelOctopi' becomes 'CamelOctopus'."""
    assert singularize("CamelOctopi") == "CamelOctopus"

def test_singularize_returns_string_type():
    """Verifies that singularize always returns a str instance."""
    assert isinstance(singularize("posts"), str)
    assert isinstance(singularize("sheep"), str)
    assert isinstance(singularize("word"), str)

def test_singularize_uncountable_check_is_case_insensitive():
    """Verifies the (?i) flag makes uncountable matching case-insensitive."""
    assert singularize("Sheep") == "Sheep"
    assert singularize("SHEEP") == "SHEEP"

def test_singularize_empty_string():
    """Verifies that an empty string passes through unchanged."""
    assert singularize("") == ""

def test_singularize_matrices_to_matrix():
    """Verifies 'matrices' -> 'matrix' via the (matr)ices$ rule."""
    assert singularize("matrices") == "matrix"

def test_singularize_vertices_to_vertex():
    """Verifies 'vertices' -> 'vertex' via the (vert|ind)ices$ rule."""
    assert singularize("vertices") == "vertex"

def test_singularize_indices_to_index():
    """Verifies 'indices' -> 'index' via the (vert|ind)ices$ rule."""
    assert singularize("indices") == "index"

def test_singularize_oxen_to_ox():
    """Verifies 'oxen' -> 'ox' via the ^(ox)en rule."""
    assert singularize("oxen") == "ox"

def test_singularize_aliases_to_alias():
    """Verifies 'aliases' -> 'alias' via the (alias)es$ rule."""
    assert singularize("aliases") == "alias"

def test_singularize_statuses_to_status():
    """Verifies 'statuses' -> 'status' via the (s)tatuses$ rule."""
    assert singularize("statuses") == "status"

def test_singularize_shoes_to_shoe():
    """Verifies 'shoes' -> 'shoe' via the (shoe)s$ rule."""
    assert singularize("shoes") == "shoe"

def test_singularize_heroes_to_hero():
    """Verifies 'heroes' -> 'hero' via the (o)es$ rule."""
    assert singularize("heroes") == "hero"

def test_singularize_potatoes_to_potato():
    """Verifies 'potatoes' -> 'potato' via the (o)es$ rule."""
    assert singularize("potatoes") == "potato"

def test_singularize_buses_to_bus():
    """Verifies 'buses' -> 'bus' via the (bus|campus)es$ rule."""
    assert singularize("buses") == "bus"

@pytest.mark.xfail(reason='code2test: possible bug - The stated intent is "Return the singular form of a word, the reverse of pluralize." The singular of "campuses" is unambiguously "campus" (drop the plural suffix "es"). The test correctly asserts this expected behavior. However, the code\'s singularization rule produces "cam', strict=False)
def test_singularize_campuses_to_campus():
    """Verifies 'campuses' -> 'campus' via the (bus|campus)es$ rule.

    NOTE: This test documents a bug in singularize(). The function returns
    'campuse' instead of 'campus' for 'campuses', which contradicts the
    stated intent of returning the singular form. The assertion of the
    intended behavior is kept unchanged.
    """
    assert singularize("campuses") == "campus"

def test_singularize_crises_to_crisis():
    """Verifies 'crises' -> 'crisis' via the (cris|ax|test)es$ rule."""
    assert singularize("crises") == "crisis"

def test_singularize_axes_to_axis():
    """Verifies 'axes' -> 'axis' via the (cris|ax|test)es$ rule."""
    assert singularize("axes") == "axis"

def test_singularize_testes_to_testis():
    """Verifies 'testes' -> 'testis' via the (cris|ax|test)es$ rule."""
    assert singularize("testes") == "testis"

def test_singularize_equipment_uncountable():
    """Verifies 'equipment' is treated as uncountable and returned unchanged."""
    assert singularize("equipment") == "equipment"

def test_singularize_fish_uncountable():
    """Verifies 'fish' is treated as uncountable and returned unchanged."""
    assert singularize("fish") == "fish"

def test_singularize_cats_via_s_rule():
    """Verifies regular plurals ending in 's' use the catch-all s$ rule."""
    assert singularize("cats") == "cat"
    assert singularize("dogs") == "dog"

def test_singularize_idempotent_for_already_singular():
    """Verifies that already-singular words are returned unchanged (idempotency)."""
    assert singularize("post") == "post"
    assert singularize("cat") == "cat"
    assert singularize("matrix") == "matrix"

def test_singularize_is_reverse_of_pluralize_for_post():
    """Verifies the documented intent: singularize is the reverse of pluralize."""
    assert singularize(pluralize("post")) == "post"
