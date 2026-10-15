"""Tests for report generation and the core data models."""

import json

from code2test.core.models import (
    Intent, TestCase as Case, TestFile as File, TestStatus as Status, TestSuite as Suite,
)
from code2test.reporting import HTMLReportGenerator, JSONReportGenerator


def make_suite():
    passed = Case(name="test_ok", intent_text="ok", test_code="def test_ok():\n    assert True\n", status=Status.PASSED)
    failed = Case(name="test_bad", intent_text="bad", test_code="def test_bad():\n    assert False\n")
    failed.mark_failed("assert False")
    files = [
        File(path="tests/test_a.py", component_id="pkg.a", component_path="pkg/a.py",
             test_cases=[passed], imports=["import pytest"], verified=True),
        File(path="tests/test_b.py", component_id="pkg.b", component_path="pkg/b.py",
             test_cases=[passed, failed], fixtures=["@pytest.fixture\ndef thing():\n    return 1"]),
    ]
    intents = {
        "pkg.a": Intent(component_id="pkg.a", component_path="pkg/a.py", intent_text="Return True if a < b", confidence=0.9),
        "pkg.b": Intent(component_id="pkg.b", component_path="pkg/b.py", intent_text="<script>x</script>", confidence=0.4),
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
    assert data["summary"] == {"module_path": "pkg", "total_tests": 3, "total_files": 2,
                               "verified_files": 1, "success_rate": 0.5}
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
