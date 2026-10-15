"""Tests for the SQLite-backed intent database and test registry."""

import pytest

from code2test.core.models import Intent, IntentEvidence, TestCase, TestFile, TestStatus
from code2test.storage import IntentDatabase, TestRegistry


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / ".code2test" / "code2test.db")


def make_intent(component_id="pkg.mod.f", confidence=0.7, path="pkg/mod.py"):
    return Intent(
        component_id=component_id,
        component_path=path,
        intent_text=f"{component_id} does things",
        confidence=confidence,
        evidence=IntentEvidence(docstring="Doc.", naming_signals=["validation"]),
    )


def make_test_file(path="tests/pkg/test_mod_f.py", component_id="pkg.mod.f"):
    return TestFile(
        path=path,
        component_id=component_id,
        component_path="pkg/mod.py",
        test_cases=[TestCase(name="test_f", intent_text="f works", test_code="def test_f():\n    assert True\n")],
        imports=["import pytest", "from pkg.mod import f"],
        fixtures=[],
    )


class TestIntentDatabase:
    def test_creates_parent_directory_and_round_trips(self, db_path):
        db = IntentDatabase(db_path)
        db.save_intent(make_intent())
        loaded = db.get_intent("pkg.mod.f")
        assert loaded.intent_text == "pkg.mod.f does things"
        assert loaded.confidence == 0.7
        assert loaded.evidence.naming_signals == ["validation"]

    def test_save_overwrites_existing_intent(self, db_path):
        db = IntentDatabase(db_path)
        intent = make_intent()
        db.save_intent(intent)
        intent.update_intent("does something else")
        db.save_intent(intent)
        loaded = db.get_intent("pkg.mod.f")
        assert loaded.intent_text == "does something else"
        assert loaded.user_edited and loaded.confidence == 0.95
        assert len(db.get_all_intents()) == 1

    def test_queries_and_stats(self, db_path):
        db = IntentDatabase(db_path)
        db.save_intent(make_intent("pkg.mod.a", 0.4))
        db.save_intent(make_intent("pkg.mod.b", 0.9))
        db.save_intent(make_intent("other.c", 0.5, path="other.py"))

        assert {i.component_id for i in db.get_low_confidence_intents(0.6)} == {"pkg.mod.a", "other.c"}
        assert {i.component_id for i in db.get_intents_by_path("pkg/")} == {"pkg.mod.a", "pkg.mod.b"}
        assert set(db.get_all_intents_dict()) == {"pkg.mod.a", "pkg.mod.b", "other.c"}
        stats = db.get_stats()
        assert stats["total_intents"] == 3
        assert stats["low_confidence"] == 2
        assert stats["avg_confidence"] == 0.6

    def test_delete_and_clear(self, db_path):
        db = IntentDatabase(db_path)
        db.save_intent(make_intent("a"))
        db.save_intent(make_intent("b"))
        assert db.delete_intent("a") is True
        assert db.delete_intent("a") is False
        db.clear_all()
        assert db.get_all_intents() == []

    def test_missing_intent_is_none(self, db_path):
        assert IntentDatabase(db_path).get_intent("nope") is None


class TestTestRegistry:
    def test_register_and_get_round_trip(self, db_path):
        registry = TestRegistry(db_path)
        registry.register_test(make_test_file())
        loaded = registry.get_test_file("tests/pkg/test_mod_f.py")
        assert loaded.component_id == "pkg.mod.f"
        assert loaded.imports == ["import pytest", "from pkg.mod import f"]
        assert [tc.name for tc in loaded.test_cases] == ["test_f"]
        assert loaded.test_cases[0].status == TestStatus.PENDING
        assert loaded.get_full_content() == make_test_file().get_full_content()

    def test_mark_verified_and_unverified_listing(self, db_path):
        registry = TestRegistry(db_path)
        registry.register_test(make_test_file("tests/a.py", "a"))
        registry.register_test(make_test_file("tests/b.py", "b"))
        assert registry.mark_verified("tests/a.py") is True
        assert registry.get_test_file("tests/a.py").verified
        assert [t.path for t in registry.get_unverified_tests()] == ["tests/b.py"]

    def test_re_registering_replaces_by_path(self, db_path):
        registry = TestRegistry(db_path)
        registry.register_test(make_test_file())
        updated = make_test_file()
        updated.test_cases.append(TestCase(name="test_g", intent_text="g", test_code="def test_g(): pass"))
        registry.register_test(updated)
        assert len(registry.get_all_tests()) == 1
        assert len(registry.get_test_file("tests/pkg/test_mod_f.py").test_cases) == 2

    def test_lookup_by_component_and_delete(self, db_path):
        registry = TestRegistry(db_path)
        registry.register_test(make_test_file())
        assert [t.path for t in registry.get_tests_for_component("pkg.mod.f")] == ["tests/pkg/test_mod_f.py"]
        assert registry.delete_test("tests/pkg/test_mod_f.py") is True
        assert registry.get_test_file("tests/pkg/test_mod_f.py") is None

    def test_intents_and_tests_share_one_database(self, db_path):
        IntentDatabase(db_path).save_intent(make_intent())
        TestRegistry(db_path).register_test(make_test_file())
        assert IntentDatabase(db_path).get_intent("pkg.mod.f") is not None
        assert TestRegistry(db_path).get_stats()["total_test_files"] == 1
