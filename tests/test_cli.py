"""CLI-level tests: `test`, `verify`, `intent` against a small sample repository."""

import importlib
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from code2test.cli.main import cli
from tests.test_pipeline import FAILING, PASSING, scripted, tests_reply

test_cmd_module = importlib.import_module("code2test.cli.commands.test")
model_module = importlib.import_module("code2test.cli.utils.model")

SOURCE = '''
def add(a: int, b: int) -> int:
    """Return the sum of a and b."""
    return a + b
'''

GENERATED = "tests/calc/test_ops_add.py"


@pytest.fixture
def repo(tmp_path, monkeypatch):
    pkg = tmp_path / "calc"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "ops.py").write_text(SOURCE)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("PYDANTIC_AI_NO_BANNER", "1")
    return tmp_path


def use_model(monkeypatch, model):
    """Make every CLI command use the given (scripted) model."""
    monkeypatch.setattr(test_cmd_module, "resolve_model", lambda display: model)
    monkeypatch.setattr(model_module, "resolve_model", lambda display: model)


def run(*args, input=None):
    return CliRunner().invoke(cli, list(args), input=input, catch_exceptions=False)


def test_auto_generates_verified_tests_then_verify_passes(repo, monkeypatch):
    use_model(monkeypatch, scripted([tests_reply(PASSING)]))

    result = run("test", "--auto", "--confidence", "0", "--exit-code", ".")
    assert result.exit_code == 0, result.output
    assert (repo / GENERATED).exists()
    assert not (repo / "tests" / "dependency_graphs").exists()  # analysis output stays in .code2test

    result = run("verify", "tests")
    assert result.exit_code == 0, result.output
    assert "1/1 tests passed" in result.output


def test_verify_fails_after_code_change_and_fix_repairs(repo, monkeypatch):
    use_model(monkeypatch, scripted([tests_reply(PASSING)]))
    assert run("test", "--auto", "--confidence", "0", ".").exit_code == 0

    # The code's behaviour changes after the tests were generated
    (repo / "calc/ops.py").write_text(SOURCE.replace("return a + b", "return a + b + 1"))

    result = run("verify", "tests")
    assert result.exit_code == 1
    assert "test_add" in result.output

    use_model(monkeypatch, scripted([tests_reply("def test_add():\n    assert add(2, 3) == 6\n")]))
    result = run("verify", "--fix", "tests")
    assert result.exit_code == 0, result.output
    assert "== 6" in (repo / GENERATED).read_text()
    assert run("verify", "tests").exit_code == 0


def test_verify_fix_does_not_overwrite_hand_edited_tests(repo, monkeypatch):
    use_model(monkeypatch, scripted([tests_reply(PASSING)]))
    assert run("test", "--auto", "--confidence", "0", ".").exit_code == 0

    edited = "from calc.ops import add\n\ndef test_add():\n    assert add(1, 1) == 3  # my edit\n"
    (repo / GENERATED).write_text(edited)

    result = run("verify", "--fix", "tests")
    assert result.exit_code == 1
    assert "edited since it was generated" in result.output
    assert (repo / GENERATED).read_text() == edited


def test_verify_diagnose_explains_failure(repo, monkeypatch):
    use_model(monkeypatch, scripted([tests_reply(PASSING)]))
    assert run("test", "--auto", "--confidence", "0", ".").exit_code == 0
    (repo / "calc/ops.py").write_text(SOURCE.replace("return a + b", "return a - b - 0"))

    use_model(monkeypatch, scripted([tests_reply(PASSING)], diagnosis="CODE_BUG"))
    result = run("verify", "--diagnose", "tests")
    assert result.exit_code == 1
    assert "add returns the wrong value" in result.output


def test_unfixable_tests_are_not_written(repo, monkeypatch):
    use_model(monkeypatch, scripted([tests_reply(FAILING)]))
    # failing test is repaired with the same failing code, then dropped: nothing is written
    result = run("test", "--auto", "--confidence", "0", "--exit-code", ".")
    assert result.exit_code == 0
    assert not (repo / GENERATED).exists()


def test_intent_show_accepts_short_names_and_modules(repo, monkeypatch):
    use_model(monkeypatch, scripted([tests_reply(PASSING)]))
    assert run("test", "--auto", "--confidence", "0", ".").exit_code == 0

    assert "calc.ops.add" in run("intent", "show", "add").output
    assert "calc.ops.add" in run("intent", "show", "calc").output
    assert "No intent found" in run("intent", "show", "nope").output


def test_interactive_mode_saves_accepted_tests(repo, monkeypatch):
    use_model(monkeypatch, scripted([tests_reply(PASSING)]))

    # confirm batch, accept intent, accept tests, confirm save
    result = run("test", ".", input="y\ny\ny\ny\n")
    assert result.exit_code == 0, result.output
    assert (repo / GENERATED).exists()


def test_interactive_mode_declined_save_leaves_no_file(repo, monkeypatch):
    use_model(monkeypatch, scripted([tests_reply(PASSING)]))

    result = run("test", ".", input="y\ny\ny\nn\n")
    assert result.exit_code == 0, result.output
    assert not (repo / GENERATED).exists()


@pytest.mark.parametrize("target", ["calc/ops.py", "calc"])
def test_file_or_subdirectory_target_uses_project_root(repo, monkeypatch, target):
    (repo / "pyproject.toml").write_text("[project]\nname = 'calc'\n")
    use_model(monkeypatch, scripted([tests_reply(PASSING)]))

    result = run("test", "--auto", "--confidence", "0", target)
    assert result.exit_code == 0, result.output
    assert (repo / GENERATED).exists()
    assert not (repo / "calc" / ".code2test").exists()


def test_intent_export_json_is_valid_json(repo, monkeypatch):
    import json

    (repo / "calc/ops.py").write_text(SOURCE.replace(
        '"""Return the sum of a and b."""',
        '"""Return the sum of a and b, which is a deliberately long sentence that would wrap in a narrow terminal."""',
    ))
    use_model(monkeypatch, scripted([tests_reply(PASSING)]))
    assert run("test", "--auto", "--confidence", "0", ".").exit_code == 0

    data = json.loads(run("intent", "export", "--format", "json").output)
    assert [i["component_id"] for i in data] == ["calc.ops.add"]
    assert "narrow terminal" in data[0]["evidence"]["docstring"]


def test_rejected_api_key_fails_the_run(repo, monkeypatch):
    from pydantic_ai.exceptions import ModelHTTPError
    from pydantic_ai.models.function import FunctionModel

    def reject(messages, info):
        raise ModelHTTPError(401, "gpt-4o-mini", {"code": "invalid_api_key"})

    use_model(monkeypatch, FunctionModel(reject))
    result = run("test", "--auto", "--confidence", "0", ".")
    assert result.exit_code == 1, result.output
    assert "HTTP 401" in result.output
    assert "Generated 0 tests" not in result.output
    assert not (repo / GENERATED).exists()


def test_benchmark_command_reports_mutation_score(repo, monkeypatch):
    import json

    use_model(monkeypatch, scripted([tests_reply(PASSING)], diagnosis="CODE_BUG"))
    assert run("test", "--auto", "--confidence", "0", ".").exit_code == 0

    result = run("benchmark", "--mutants", "5", "--diagnoses", "1", ".")
    assert result.exit_code == 0, result.output
    assert "Mutants killed" in result.output
    data = json.loads((repo / ".code2test" / "benchmark.json").read_text())
    assert data["mutants_total"] == 2 and data["mutants_killed"] == 2
    assert data["generation"]["acceptance_rate"] == 1.0



def test_report_coverage_in_text_json_and_html(repo, monkeypatch):
    use_model(monkeypatch, scripted([tests_reply(PASSING)]))
    assert run("test", "--auto", "--confidence", "0", ".").exit_code == 0

    result = run("report", "coverage")
    assert result.exit_code == 0, result.output
    assert "calc.ops.add" in result.output and "Run 'code2test benchmark'" in result.output

    # After a benchmark, the mutation score and diagnostic accuracy appear
    assert run("benchmark", "--diagnoses", "0", ".").exit_code == 0
    result = run("report", "coverage")
    assert "Mutation score: 100%" in result.output and "Diagnostic accuracy: n/a" in result.output

    assert run("report", "coverage", "--format", "json").exit_code == 0
    data = json.loads((repo / "tests/reports/coverage.json").read_text())
    component = data["components"][0]
    assert component["component"] == "calc.ops.add" and component["tests_passing"] == 1
    assert component["mutants"] == component["mutants_killed"] > 0

    assert run("report", "coverage", "--format", "html", "--output", "cov.html").exit_code == 0
    assert "Test Quality" in (repo / "cov.html").read_text()


class _Display:
    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(message)

    warning = success = error = info


@pytest.fixture
def no_saved_config(tmp_path, monkeypatch):
    config_module = importlib.import_module("code2test.cli.config_manager")
    monkeypatch.setattr(config_module, "CONFIG_FILE", tmp_path / "none" / "config.json")
    monkeypatch.setattr(config_module.ConfigManager, "get_api_key", lambda self: None)
    for var in ("CODE2TEST_MODEL", "LLM_BACKEND", "AZURE_OPENAI_DEPLOYMENT", "AZURE_OPENAI_ENDPOINT"):
        monkeypatch.delenv(var, raising=False)


def test_resolve_model_uses_code2test_model_without_warnings(no_saved_config, monkeypatch):
    monkeypatch.setenv("CODE2TEST_MODEL", "anthropic:claude-sonnet-5-5")
    display = _Display()
    assert model_module.resolve_model(display) == "anthropic:claude-sonnet-5-5"
    assert display.messages == []


def test_resolve_model_says_when_it_falls_back_to_the_default(no_saved_config):
    display = _Display()
    assert model_module.resolve_model(display) == "openai:gpt-4o-mini"
    assert len(display.messages) == 1 and "No model configured" in display.messages[0]
