"""Tests for running generated tests with pytest (core/verifier.py, PytestAdapter)."""

import pytest

from code2test.adapters.python.pytest_adapter import PytestAdapter
from code2test.core.models import TestCase as Case, TestFile as File, TestStatus as Status
from code2test.core.verifier import TestVerifier


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "calc").mkdir()
    (tmp_path / "calc" / "__init__.py").write_text("")
    (tmp_path / "calc" / "ops.py").write_text("def add(a, b):\n    return a + b\n")
    return tmp_path


def make_file(*cases, imports=("from calc.ops import add",), path="tests/test_add.py"):
    return File(
        path=path, component_id="calc.ops.add", component_path="calc/ops.py",
        imports=list(imports),
        test_cases=[Case(name=name, intent_text="", test_code=code) for name, code in cases],
    )


def test_passing_and_failing_tests_get_their_own_status(repo):
    tf = make_file(
        ("test_ok", "def test_ok():\n    assert add(1, 2) == 3\n"),
        ("test_bad", "def test_bad():\n    assert add(1, 2) == 4\n"),
    )
    result = TestVerifier(str(repo)).run_tests(tf)

    assert not result.all_passed
    assert result.passed == ["test_ok"] and result.failed == ["test_bad"]
    ok, bad = tf.test_cases
    assert ok.status == Status.PASSED
    assert bad.status == Status.FAILED and "assert 3 == 4" in bad.failure_message
    assert (repo / "tests/test_add.py").read_text() == tf.get_full_content()


def test_collection_error_is_attributed_to_every_test(repo):
    tf = make_file(("test_ok", "def test_ok():\n    assert True\n"), imports=["from calc.nope import add"])
    result = TestVerifier(str(repo)).run_tests(tf)
    assert not result.all_passed
    assert tf.test_cases[0].status == Status.FAILED
    assert "calc.nope" in tf.test_cases[0].failure_message


def test_xfail_counts_as_verified(repo):
    tf = make_file(
        ("test_bug", "@pytest.mark.xfail(reason='known bug')\ndef test_bug():\n    assert add(1, 1) == 3\n"),
        imports=["import pytest", "from calc.ops import add"],
    )
    result = TestVerifier(str(repo)).run_tests(tf)
    assert result.all_passed and result.skipped == ["test_bug"]


def test_file_without_tests_is_not_verified(repo):
    result = TestVerifier(str(repo)).run_tests(make_file())
    assert not result.all_passed


def test_target_repo_addopts_are_ignored(repo):
    (repo / "pytest.ini").write_text("[pytest]\naddopts = --plugin-that-does-not-exist\n")
    tf = make_file(("test_ok", "def test_ok():\n    assert add(1, 2) == 3\n"))
    assert TestVerifier(str(repo)).run_tests(tf).all_passed


def test_src_layout_is_importable(tmp_path):
    (tmp_path / "src" / "calc").mkdir(parents=True)
    (tmp_path / "src" / "calc" / "__init__.py").write_text("")
    (tmp_path / "src" / "calc" / "ops.py").write_text("def add(a, b):\n    return a + b\n")
    tf = make_file(("test_ok", "def test_ok():\n    assert add(1, 2) == 3\n"))
    assert TestVerifier(str(tmp_path)).run_tests(tf).all_passed


def test_rewritten_file_is_not_served_from_stale_bytecode(repo):
    verifier = TestVerifier(str(repo))
    first = make_file(("test_x", "def test_x():\n    assert add(1, 1) == 2\n"))
    assert verifier.run_tests(first).all_passed
    # same size, same second: a stale .pyc would still pass
    second = make_file(("test_x", "def test_x():\n    assert add(1, 1) == 3\n"))
    assert not verifier.run_tests(second).all_passed


def test_timeout_is_reported_as_failure(repo):
    tf = make_file(("test_slow", "def test_slow():\n    import time\n    time.sleep(30)\n"))
    result = TestVerifier(str(repo), timeout=3).run_tests(tf)
    assert not result.all_passed
    assert "timed out" in tf.test_cases[0].failure_message


def test_syntax_validation():
    good = make_file(("test_ok", "def test_ok():\n    pass\n"))
    bad = make_file(("test_bad", "def test_bad(:\n    pass\n"))
    verifier = TestVerifier(".")
    assert verifier.validate_syntax(good) == (True, None)
    ok, message = verifier.validate_syntax(bad)
    assert not ok and "Syntax error" in message


def test_pytest_adapter_summarizes_a_directory(repo):
    tests = repo / "tests"
    tests.mkdir()
    (tests / "test_a.py").write_text(
        "from calc.ops import add\n\ndef test_ok():\n    assert add(1, 1) == 2\n\ndef test_bad():\n    assert add(1, 1) == 3\n"
    )
    results = PytestAdapter(str(repo)).run_tests("tests")
    assert results["success"] is False
    assert results["summary"] == {"passed": 1, "failed": 1, "skipped": 0, "total": 2}
    assert {t["outcome"] for t in results["tests"]} == {"passed", "failed"}
