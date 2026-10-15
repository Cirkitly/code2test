"""Tests for report generation and the core data models."""

import json

import os

from code2test.core.models import (
    Diagnosis,
    DiagnosisCause,
    Intent,
    TestCase as Case,
    TestFile as File,
    TestStatus as Status,
    TestSuite as Suite,
)
from code2test.core.quality import quality_report
from code2test.reporting import HTMLReportGenerator, JSONReportGenerator


def make_suite():
    passed = Case(
        name="test_ok",
        intent_text="ok",
        test_code="def test_ok():\n    assert True\n",
        status=Status.PASSED,
    )
    failed = Case(
        name="test_bad", intent_text="bad", test_code="def test_bad():\n    assert False\n"
    )
    failed.mark_failed("assert False")
    files = [
        File(
            path="tests/test_a.py",
            component_id="pkg.a",
            component_path="pkg/a.py",
            test_cases=[passed],
            imports=["import pytest"],
            verified=True,
        ),
        File(
            path="tests/test_b.py",
            component_id="pkg.b",
            component_path="pkg/b.py",
            test_cases=[passed, failed],
            fixtures=["@pytest.fixture\ndef thing():\n    return 1"],
        ),
    ]
    intents = {
        "pkg.a": Intent(
            component_id="pkg.a",
            component_path="pkg/a.py",
            intent_text="Return True if a < b",
            confidence=0.9,
        ),
        "pkg.b": Intent(
            component_id="pkg.b",
            component_path="pkg/b.py",
            intent_text="<script>x</script>",
            confidence=0.4,
        ),
    }
    return Suite(module_path="pkg", test_files=files, intents=intents), intents


def test_test_file_content_and_counts():
    suite, _ = make_suite()
    b = suite.test_files[1]
    assert b.total_tests == 2 and b.passed_count == 1 and b.failed_count == 1
    content = b.get_full_content()
    assert content.index("def thing") < content.index("def test_ok") < content.index("def test_bad")
    compile(content, b.path, "exec")
    assert suite.total_tests == 3 and suite.total_passed == 2
    assert suite.coverage_summary["components_with_tests"] == 2


def test_failed_case_keeps_message_and_passing_clears_it():
    case = Case(name="t", intent_text="", test_code="")
    case.mark_failed("boom")
    assert case.status == Status.FAILED and case.failure_message == "boom"
    case.mark_passed()
    assert case.status == Status.PASSED and case.failure_message is None


def test_user_edit_makes_intent_confident():
    intent = Intent(component_id="x", component_path="x.py", intent_text="old", confidence=0.3)
    assert intent.needs_clarification()
    intent.update_intent("new")
    assert intent.intent_text == "new" and intent.user_edited and not intent.needs_clarification()


def test_json_report(tmp_path):
    suite, intents = make_suite()
    out = tmp_path / "report.json"
    data = JSONReportGenerator().generate_report(suite, intents, str(out))
    assert json.loads(out.read_text()) == json.loads(json.dumps(data, default=str))
    assert data["summary"] == {
        "module_path": "pkg",
        "total_tests": 3,
        "total_files": 2,
        "verified_files": 1,
        "success_rate": 0.5,
    }
    assert data["files"][1]["test_cases"][1] == {"name": "test_bad", "status": "failed"}
    assert data["intents"]["pkg.a"]["confidence"] == 0.9


def test_html_report_escapes_code_text(tmp_path):
    suite, intents = make_suite()
    out = tmp_path / "report.html"
    html = HTMLReportGenerator().generate_report(suite, intents, str(out))
    assert out.read_text() == html
    assert "tests/test_b.py" in html and "pkg.a" in html
    assert "<script>x</script>" not in html
    assert "a &lt; b" in html


def _quality_repo(tmp_path, benchmark=True):
    state = tmp_path / ".code2test"
    state.mkdir(parents=True)
    (state / "metrics.json").write_text("{}")
    if benchmark:
        (state / "benchmark.json").write_text(
            json.dumps(
                {
                    "created_at": "2026-10-15T12:00:00+00:00",
                    "mutation_score": 0.75,
                    "mutants_killed": 3,
                    "mutants_total": 4,
                    "diagnosis_accuracy": 0.5,
                    "diagnosis_by_expected_cause": {
                        "CODE_BUG": {"cases": 2, "correct": 1, "unscored": 0}
                    },
                    "by_component": {
                        "pkg.a": {"mutants": 4, "killed": 3, "killed_by_own_tests": 2}
                    },
                }
            )
        )
        os.utime(state / "metrics.json", (1, 1))  # the benchmark ran after the last generation
    return tmp_path


def _quality_files():
    def case(name, behavior, status=Status.PASSED, code="assert True", diagnosis=None):
        return Case(
            name=name,
            intent_text=behavior,
            test_code=f"def {name}():\n    {code}\n",
            status=status,
            diagnosis=diagnosis,
        )

    bug = Diagnosis(
        test_name="test_bug",
        cause=DiagnosisCause.CODE_BUG,
        confidence=0.9,
        explanation="wrong output",
    )
    return [
        File(
            path="tests/test_a.py",
            component_id="pkg.a",
            component_path="pkg/a.py",
            test_cases=[
                case("test_one", "Returns the sum"),
                case("test_two", "returns  the SUM"),  # same behavior, other wording
                case("test_three", "Rejects strings"),
                case("test_skip", "Handles None", status=Status.SKIPPED),
                case("test_bug", "Rounds halves up", status=Status.XFAIL, diagnosis=bug),
            ],
        )
    ]


def test_quality_report_counts_distinct_behaviors_of_passing_tests(tmp_path):
    _, intents = make_suite()
    quality = quality_report(_quality_repo(tmp_path), _quality_files(), intents)

    a = next(c for c in quality["components"] if c["component"] == "pkg.a")
    assert a["behaviors_tested"] == ["Returns the sum", "Rejects strings"]
    assert a["tests_passing"] == 3 and a["tests_xfail"] == 1
    assert (a["mutants"], a["mutants_killed"], a["mutation_score"]) == (4, 3, 0.75)
    b = next(c for c in quality["components"] if c["component"] == "pkg.b")
    assert (
        b["behaviors_tested"] == [] and b["mutants"] is None and b["intent"] == "<script>x</script>"
    )

    assert quality["summary"] == {
        "components": 2,
        "components_with_passing_tests": 1,
        "behaviors_tested": 2,
        "mutation_score": 0.75,
        "diagnosis_accuracy": 0.5,
    }
    assert quality["benchmark"]["available"] and not quality["benchmark"]["stale"]
    assert quality["benchmark"]["created_at"] == "2026-10-15T12:00:00+00:00"


def test_quality_report_without_benchmark_and_with_a_stale_one(tmp_path):
    _, intents = make_suite()
    quality = quality_report(
        _quality_repo(tmp_path / "none", benchmark=False), _quality_files(), intents
    )
    assert quality["benchmark"] == {"available": False, "stale": False}
    assert quality["summary"]["mutation_score"] is None

    repo = _quality_repo(tmp_path / "stale")
    os.utime(repo / ".code2test" / "benchmark.json", (0, 0))  # generation ran after the benchmark
    assert quality_report(repo, _quality_files(), intents)["benchmark"]["stale"]


def test_reports_include_quality(tmp_path):
    suite, intents = make_suite()
    quality = quality_report(_quality_repo(tmp_path), _quality_files(), intents)

    data = JSONReportGenerator().generate_report(
        suite, intents, str(tmp_path / "r.json"), quality=quality
    )
    assert data["quality"]["summary"]["behaviors_tested"] == 2

    html = HTMLReportGenerator().generate_report(
        suite, intents, str(tmp_path / "r.html"), quality=quality
    )
    assert "Test Quality" in html and "Returns the sum" in html and "3/4 (75%)" in html
    assert "<script>x</script>" not in html

    page = HTMLReportGenerator().generate_quality_report(quality, str(tmp_path / "c.html"))
    assert "Diagnostic Accuracy" in page and "50%" in page
    assert (
        JSONReportGenerator().generate_quality_report(quality, str(tmp_path / "c.json"))["summary"]
        == quality["summary"]
    )
