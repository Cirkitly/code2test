"""Tests for run metrics and the benchmark (mutation score, diagnosis accuracy)."""

import asyncio
import json

from code2test.core.benchmark import Benchmark, break_expected_value, generate_mutants
from code2test.core.metrics import FileMetrics, RunMetrics
from code2test.core.models import TestCase as Case, TestFile as File
from tests.test_pipeline import FAILING, PASSING, _make_repo, _run, scripted, tests_reply


def test_metrics_record_first_run_and_repairs(tmp_path):
    repo = _make_repo(tmp_path)
    gen_model = scripted([tests_reply(FAILING), tests_reply(PASSING)])
    _run(repo, gen_model)

    data = json.loads((repo / ".code2test" / "metrics.json").read_text())
    assert data["summary"]["components"] == 1
    assert data["summary"]["components_with_tests"] == 1
    assert data["summary"]["acceptance_rate"] == 1.0
    assert data["summary"]["tests_generated"] == 1
    assert data["summary"]["first_run_passed"] == 0
    assert data["summary"]["first_run_pass_rate"] == 0.0
    assert data["summary"]["tests_kept"] == 1
    assert data["summary"]["repair_rounds"] == 1


def test_metrics_count_discarded_files(tmp_path):
    repo = _make_repo(tmp_path)
    _run(repo, scripted([tests_reply(FAILING)], diagnosis="TEST_WRONG"))
    summary = json.loads((repo / ".code2test" / "metrics.json").read_text())["summary"]
    assert summary["acceptance_rate"] == 0.0
    assert summary["tests_dropped"] == 1 and summary["files_removed"] == 1
    assert summary["diagnoses"] == {"TEST_WRONG": 1}


def test_only_really_passing_tests_make_a_component_accepted():
    metrics = RunMetrics(components=3)
    metrics.files["a"] = FileMetrics(component_id="a", path="a", generated=2, kept=2, xfail=2, passing=0)
    metrics.files["b"] = FileMetrics(component_id="b", path="b", generated=1, kept=1, passing=1)
    metrics.files["c"] = FileMetrics(component_id="c", path="c", generated=1, kept=1, passing=0)  # only skipped tests
    assert metrics.components_with_tests == 1
    assert metrics.acceptance_rate == 1 / 3


def test_rates_are_none_when_nothing_was_generated():
    metrics = RunMetrics(components=0)
    assert metrics.acceptance_rate is None and metrics.first_run_pass_rate is None
    assert metrics.summary()["first_run_pass_rate"] is None


def test_mutants_change_one_site_each(tmp_path):
    (tmp_path / "m.py").write_text(
        'def check(x):\n    """Doc."""\n    if x > 3:\n        return x + 1\n    return "low"\n\n'
        "def untested():\n    return 1 + 1\n"
    )
    mutants = generate_mutants(tmp_path, "m.py", {"check": "m.check"})
    descriptions = {m.description for m in mutants}
    assert "Gt -> LtE" in descriptions
    assert "Add -> Sub" in descriptions
    assert "3 -> 4" in descriptions
    assert "'low' -> 'lo'" in descriptions
    assert "return value -> None" in descriptions
    assert all(m.component_id == "m.check" for m in mutants)  # untested() is never mutated
    assert all('"""Doc."""' in m.source or "'Doc.'" in m.source for m in mutants)  # docstrings are left alone


def test_break_expected_value():
    assert break_expected_value("def test_x():\n    assert f(2) == 5\n") == "def test_x():\n    assert f(2) == 6"
    assert "== 'a'" in break_expected_value("def test_x():\n    assert f() == 'ab'\n")
    assert break_expected_value("def test_x():\n    assert f()\n") is None


def _benchmark_repo(tmp_path):
    repo = _make_repo(tmp_path)
    tf = File(
        path="tests/calc/test_ops_add.py", component_id="calc.ops.add", component_path="calc/ops.py",
        imports=["import pytest", "from calc.ops import add"], verified=True,
        test_cases=[Case(name="test_add", intent_text="sum", test_code=PASSING)],
    )
    (repo / tf.path).parent.mkdir(parents=True)
    (repo / tf.path).write_text(tf.get_full_content())
    from code2test.core.models import Intent

    intents = {"calc.ops.add": Intent(component_id="calc.ops.add", component_path="calc/ops.py",
                                      intent_text="Return the sum", confidence=0.9)}
    components = {"calc.ops.add": {"id": "calc.ops.add", "name": "add", "relative_path": "calc/ops.py",
                                   "source_code": "def add(a, b):\n    return a + b\n"}}
    return repo, tf, intents, components


def test_benchmark_kills_mutants_and_restores_source(tmp_path):
    repo, tf, intents, components = _benchmark_repo(tmp_path)
    original = (repo / "calc/ops.py").read_text()

    result = asyncio.run(Benchmark(repo, [tf], intents, components).run(max_mutants=10))

    assert result.mutants_total == 2  # a + b -> a - b, return value -> None
    assert result.mutants_killed == 2 and result.mutation_score == 1.0
    assert (repo / "calc/ops.py").read_text() == original
    assert result.by_component == {"calc.ops.add": {"mutants": 2, "killed": 2, "killed_by_own_tests": 2}}
    data = result.to_dict()
    assert data["by_component"] == result.by_component and data["created_at"]


def test_benchmark_scores_diagnoses_against_known_causes(tmp_path):
    from code2test.agents.diagnosis_agent import DiagnosisAgent

    repo, tf, intents, components = _benchmark_repo(tmp_path)
    agent = DiagnosisAgent(model=scripted([tests_reply(PASSING)], diagnosis="CODE_BUG"))

    result = asyncio.run(Benchmark(repo, [tf], intents, components, diagnosis_agent=agent)
                         .run(max_mutants=10, max_diagnoses=1))

    expected = sorted(c.expected for c in result.diagnosis_cases)
    assert expected == ["CODE_BUG", "TEST_WRONG"]
    assert result.diagnosis_accuracy == 0.5  # always answering CODE_BUG gets only the code-bug case right
    assert not list((repo / "tests/calc").glob("_c2t_probe_*"))


def test_unchanged_rerun_counts_already_verified_components(tmp_path):
    repo = _make_repo(tmp_path)
    _run(repo, scripted([tests_reply(PASSING)]))
    _run(repo, scripted([tests_reply(PASSING)]))  # nothing changed: the component is skipped

    summary = json.loads((repo / ".code2test" / "metrics.json").read_text())["summary"]
    assert summary["acceptance_rate"] == 1.0
    assert summary["components_reused"] == 1
    assert summary["tests_generated"] == 0 and summary["first_run_pass_rate"] is None


def test_skipped_tests_do_not_count_as_passing(tmp_path):
    repo = _make_repo(tmp_path)
    skip = "def test_add():\n    pytest.skip('needs a database')\n"
    _run(repo, scripted([tests_reply(skip, imports=["import pytest", "from calc.ops import add"])]))

    summary = json.loads((repo / ".code2test" / "metrics.json").read_text())["summary"]
    assert summary["first_run_passed"] == 0
    assert summary["components_with_tests"] == 0


def test_one_syntax_error_does_not_hide_the_other_tests_first_run(tmp_path):
    repo = _make_repo(tmp_path)
    reply = {
        "tests": [
            {"name": "test_ok", "description": "", "test_code": "def test_ok():\n    assert add(1, 1) == 2\n", "tests_behavior": ""},
            {"name": "test_broken", "description": "", "test_code": "def test_broken(:\n    pass\n", "tests_behavior": ""},
        ],
        "imports": ["from calc.ops import add"],
    }
    _run(repo, scripted([reply, tests_reply(PASSING)]))
    summary = json.loads((repo / ".code2test" / "metrics.json").read_text())["summary"]
    assert summary["tests_generated"] == 2
    assert summary["first_run_passed"] == 1


def test_annotation_constants_are_not_mutated(tmp_path):
    (tmp_path / "m.py").write_text(
        'def make(kind: "str") -> "Node":\n    if kind == "leaf":\n        return 1\n    return 2\n'
    )
    descriptions = {m.description for m in generate_mutants(tmp_path, "m.py", {"make": "m.make"})}
    assert "'leaf' -> 'lea'" in descriptions
    assert not any("'Node'" in d or "'str'" in d for d in descriptions)


def test_break_expected_value_skips_empty_strings():
    code = "def test_x():\n    assert strip('  ') == ''\n    assert add(2, 3) == 5\n"
    assert break_expected_value(code).endswith("== 6")


def test_benchmark_restores_crlf_source_byte_for_byte(tmp_path):
    repo, tf, intents, components = _benchmark_repo(tmp_path)
    source = repo / "calc/ops.py"
    source.write_bytes(b"def add(a, b):\r\n    return a + b\r\n")
    original = source.read_bytes()

    asyncio.run(Benchmark(repo, [tf], intents, components).run(max_mutants=10))

    assert source.read_bytes() == original
    assert not (repo / ".code2test" / "benchmark_backup").exists()


def test_benchmark_restores_files_left_mutated_by_a_killed_run(tmp_path):
    repo, tf, intents, components = _benchmark_repo(tmp_path)
    source = repo / "calc/ops.py"
    original = source.read_bytes()
    backup = repo / ".code2test" / "benchmark_backup" / "calc" / "ops.py"
    backup.parent.mkdir(parents=True)
    backup.write_bytes(original)
    source.write_text("def add(a, b):\n    return None\n")  # what a killed run leaves behind

    result = asyncio.run(Benchmark(repo, [tf], intents, components).run(max_mutants=10))

    assert result.restored_files == ["calc/ops.py"]
    assert source.read_bytes() == original
    assert result.mutants_killed == result.mutants_total == 2


def test_failed_diagnosis_calls_are_not_scored(tmp_path):
    from code2test.agents.diagnosis_agent import DiagnosisAgent

    repo, tf, intents, components = _benchmark_repo(tmp_path)

    def broken(messages, info):
        raise RuntimeError("provider overloaded")

    from pydantic_ai.models.function import FunctionModel

    result = asyncio.run(Benchmark(repo, [tf], intents, components,
                                   diagnosis_agent=DiagnosisAgent(model=FunctionModel(broken)))
                         .run(max_mutants=10, max_diagnoses=1))
    assert result.diagnosis_cases and all(c.actual is None for c in result.diagnosis_cases)
    assert result.diagnosis_accuracy is None
    assert result.to_dict()["diagnosis_by_expected_cause"]["CODE_BUG"] == {"cases": 0, "correct": 0, "unscored": 1}


def test_unreachable_model_keeps_mutation_results(tmp_path):
    from code2test.agents.diagnosis_agent import DiagnosisAgent
    from code2test.agents.errors import ModelAccessError

    repo, tf, intents, components = _benchmark_repo(tmp_path)

    class Unreachable(DiagnosisAgent):
        async def diagnose_failure(self, *args, **kwargs):
            raise ModelAccessError("HTTP 401")

    result = asyncio.run(Benchmark(repo, [tf], intents, components, diagnosis_agent=Unreachable())
                         .run(max_mutants=10, max_diagnoses=1))
    assert result.mutants_total == 2 and result.mutants_killed == 2
    assert result.diagnosis_error == "HTTP 401"


def test_wrong_test_probe_keeps_helpers_from_sibling_tests(tmp_path):
    from code2test.agents.diagnosis_agent import DiagnosisAgent

    repo, tf, intents, components = _benchmark_repo(tmp_path)
    tf.test_cases = [
        Case(name="test_helper", intent_text="", test_code="TWO = 2\n\ndef test_helper():\n    assert TWO == 2\n"),
        Case(name="test_add", intent_text="", test_code="def test_add():\n    assert add(TWO, 3) == 5\n"),
    ]
    (repo / tf.path).write_text(tf.get_full_content())
    agent = DiagnosisAgent(model=scripted([tests_reply(PASSING)], diagnosis="TEST_WRONG"))

    result = asyncio.run(Benchmark(repo, [tf], intents, components, diagnosis_agent=agent)
                         .run(max_mutants=0, max_diagnoses=5))
    wrong = [c for c in result.diagnosis_cases if c.expected == "TEST_WRONG"]
    assert {c.test for c in wrong} == {"test_helper", "test_add"}  # test_add's probe still sees TWO


def test_benchmark_skips_components_outside_the_repo(tmp_path):
    repo, tf, intents, components = _benchmark_repo(tmp_path)
    tf.component_path = "/somewhere/else/calc/ops.py"
    result = asyncio.run(Benchmark(repo, [tf], intents, components).run(max_mutants=10))
    assert result.mutants_total == 0


def test_mutants_run_against_the_whole_generated_suite(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "calc/ops.py").write_text("def helper(x):\n    return x + 1\n\n\ndef add_one(x):\n    return helper(x)\n")
    weak = File(path="tests/calc/test_ops_helper.py", component_id="calc.ops.helper", component_path="calc/ops.py",
                imports=["from calc.ops import helper"],
                test_cases=[Case(name="test_helper", intent_text="", test_code="def test_helper():\n    assert callable(helper)\n")])
    strong = File(path="tests/calc/test_ops_add_one.py", component_id="calc.ops.add_one", component_path="calc/ops.py",
                  imports=["from calc.ops import add_one"],
                  test_cases=[Case(name="test_add_one", intent_text="", test_code="def test_add_one():\n    assert add_one(1) == 2\n")])
    for tf in (weak, strong):
        (repo / tf.path).parent.mkdir(parents=True, exist_ok=True)
        (repo / tf.path).write_text(tf.get_full_content())
    bench = Benchmark(repo, [weak, strong], {}, {})
    helper_mutants = [m for m in bench.mutants(100) if m.component_id == "calc.ops.helper"]
    assert helper_mutants

    result = asyncio.run(bench.run(max_mutants=100))
    # helper's own (weak) test misses its bugs, but add_one's test catches them
    assert result.mutants_killed == result.mutants_total
    assert result.mutants_killed_by_own_tests < result.mutants_killed
