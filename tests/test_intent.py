"""Tests for static intent extraction (core/intent.py and the Python analyzer)."""

import pytest

from code2test.core.intent import IntentExtractor, first_docstring_sentence
from code2test.core.intent_analyzers import JavaAnalyzer, JavascriptAnalyzer, PythonAnalyzer

TYPED = '''def add(a: int, b: int) -> int:
    """Return the sum of a and b."""
    return a + b
'''
UNTYPED = "def add(a, b):\n    return a + b\n"


def component(**overrides):
    base = {
        "id": "calc.ops.add",
        "name": "add",
        "component_type": "function",
        "file_path": "/repo/calc/ops.py",
        "source_code": TYPED,
        "docstring": "Return the sum of a and b.",
    }
    base.update(overrides)
    return base


@pytest.fixture
def extractor():
    return IntentExtractor(confidence_threshold=0.6)


def test_signature_is_derived_from_source_when_missing():
    analyzer = PythonAnalyzer()
    assert analyzer.extract_signature(component()) == "def add(a: int, b: int) -> int"
    assert analyzer.extract_type_hints(component()) == "def add(a: int, b: int) -> int"


def test_untyped_source_has_signature_but_no_type_hints():
    analyzer = PythonAnalyzer()
    comp = component(source_code=UNTYPED)
    assert analyzer.extract_signature(comp) == "def add(a, b)"
    assert analyzer.extract_type_hints(comp) == ""


def test_class_and_async_signatures():
    analyzer = PythonAnalyzer()
    assert (
        analyzer.extract_signature(component(source_code="class Foo(Base, Mixin):\n    pass\n"))
        == "class Foo(Base, Mixin)"
    )
    assert (
        analyzer.extract_signature(
            component(source_code="async def fetch(url: str) -> bytes:\n    ...\n")
        )
        == "async def fetch(url: str) -> bytes"
    )


def test_indented_method_source_is_parsed():
    method = "    def area(self) -> float:\n        return 1.0\n"
    assert (
        PythonAnalyzer().extract_signature(component(source_code=method))
        == "def area(self) -> float"
    )


def test_type_hints_raise_confidence(extractor):
    typed = extractor.extract_intent(component())
    untyped = extractor.extract_intent(component(source_code=UNTYPED))
    assert typed.confidence == pytest.approx(untyped.confidence + IntentExtractor.TYPE_HINT_WEIGHT)
    assert typed.evidence.type_hints == "def add(a: int, b: int) -> int"


def test_documented_typed_function_clears_default_threshold(extractor):
    intent = extractor.extract_intent(component())
    assert not intent.needs_clarification(0.6)
    assert intent.intent_text == "Return the sum of a and b"


def test_naming_convention_is_a_signal(extractor):
    intent = extractor.extract_intent(
        component(name="validate_email", docstring="", source_code="def validate_email(s): ...")
    )
    assert "validation" in intent.evidence.naming_signals
    assert intent.intent_text == "Performs validation operation"


def test_fallback_text_uses_component_type(extractor):
    intent = extractor.extract_intent(
        component(
            name="Widget",
            component_type="class",
            docstring=None,
            source_code="class Widget:\n    pass\n",
        )
    )
    assert intent.intent_text == "Class 'Widget'"


def test_missing_fields_do_not_crash(extractor):
    intent = extractor.extract_intent(
        {
            "id": "x",
            "name": "x",
            "language": None,
            "docstring": None,
            "source_code": None,
            "file_path": None,
            "called_by": None,
        }
    )
    assert 0.1 <= intent.confidence <= 0.99


def test_complexity_lowers_confidence(extractor):
    simple = extractor.extract_intent(component())
    complex_ = extractor.extract_intent(component(cyclomatic_complexity=12))
    assert complex_.confidence == pytest.approx(
        simple.confidence - IntentExtractor.COMPLEXITY_PENALTY
    )


def test_call_sites_raise_confidence(extractor):
    lonely = extractor.extract_intent(component(source_code=UNTYPED, docstring=""))
    called = extractor.extract_intent(
        component(source_code=UNTYPED, docstring="", called_by=["a", "b", "c"])
    )
    assert called.confidence == pytest.approx(lonely.confidence + IntentExtractor.CALL_SITE_WEIGHT)
    assert called.evidence.call_sites == ["a", "b", "c"]


def test_dependency_intents_are_recorded_as_evidence(extractor):
    dep = extractor.extract_intent(component(id="calc.ops.helper", name="helper"))
    intent = extractor.extract_intent(component(), {"calc.ops.helper": dep})
    assert intent.evidence.dependency_intents == [f"calc.ops.helper: {dep.intent_text}"]


@pytest.mark.parametrize(
    "file_path, language, expected",
    [
        ("a/b.py", None, PythonAnalyzer),
        ("a/b.ts", None, JavascriptAnalyzer),
        ("a/B.java", None, JavaAnalyzer),
        ("a/b.unknown", "java", JavaAnalyzer),
        ("a/b.unknown", None, PythonAnalyzer),
    ],
)
def test_analyzer_selection(extractor, file_path, language, expected):
    assert isinstance(
        extractor._get_analyzer({"file_path": file_path, "language": language}), expected
    )


def test_clarification_questions_cover_missing_evidence(extractor):
    comp = component(docstring="", source_code=UNTYPED, cyclomatic_complexity=7)
    intent = extractor.extract_intent(comp)
    questions = extractor.get_clarification_questions(intent, comp)
    assert any("primary purpose" in q for q in questions)
    assert any("types of inputs" in q for q in questions)
    assert any("complex logic" in q for q in questions)


@pytest.mark.parametrize(
    "docstring, expected",
    [
        ("Return the sum of a and b.", "Return the sum of a and b"),
        # Decimals and abbreviations do not end the sentence
        (
            "Return the total plus tax at rate (0.2 means 20%), rounded.",
            "Return the total plus tax at rate (0.2 means 20%), rounded",
        ),
        ("Format an amount, e.g. '12.50 USD'. More.", "Format an amount, e.g. '12.50 USD'"),
        # Wrapped lines are joined; later paragraphs are ignored
        (
            "Add rules for plurals and singular\nfor irregular words.\n\n:param word: x",
            "Add rules for plurals and singular for irregular words",
        ),
        ("Is it valid? More text.", "Is it valid"),
        ("No period at all", "No period at all"),
    ],
)
def test_first_docstring_sentence(docstring, expected):
    assert first_docstring_sentence(docstring) == expected
